#include <arpa/inet.h>
#include <openssl/cms.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "coretrust_templates/CADetails.h"
#include "coretrust_templates/TemplateSignatureBlob.h"

static int read_file(const char *path, unsigned char **data, size_t *size) {
    FILE *file = fopen(path, "rb");
    long length;
    if (!file) return -1;
    if (fseek(file, 0, SEEK_END) || (length = ftell(file)) < 0 || fseek(file, 0, SEEK_SET)) {
        fclose(file);
        return -1;
    }
    *data = malloc((size_t)length);
    if (!*data || fread(*data, 1, (size_t)length, file) != (size_t)length) {
        free(*data);
        fclose(file);
        return -1;
    }
    fclose(file);
    *size = (size_t)length;
    return 0;
}

static int digest(const EVP_MD *algorithm, const unsigned char *data, size_t size,
                  unsigned char *output, unsigned int expected) {
    unsigned int length = 0;
    if (!EVP_Digest(data, size, output, &length, algorithm, NULL)) return -1;
    return length == expected ? 0 : -1;
}

static void base64(const unsigned char *data, int size, char *output) {
    EVP_EncodeBlock((unsigned char *)output, data, size);
}

static int write_blob(const char *path, const unsigned char *der, int der_size) {
    FILE *file = fopen(path, "wb");
    uint32_t header[2] = {htonl(0xfade0b01U), htonl((uint32_t)der_size + 8U)};
    if (!file) return -1;
    if (fwrite(header, 1, sizeof(header), file) != sizeof(header) ||
        fwrite(der, 1, (size_t)der_size, file) != (size_t)der_size || fclose(file)) {
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    unsigned char *sha1_cd = NULL, *sha256_cd = NULL, *der_output = NULL;
    size_t sha1_size = 0, sha256_size = 0;
    unsigned char sha1_hash[20], sha256_hash[32], hashes_der[78] = {
        0x30,0x1d,0x06,0x05,0x2b,0x0e,0x03,0x02,0x1a,0x04,0x14,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0x30,0x2d,0x06,0x09,0x60,0x86,0x48,0x01,0x65,0x03,0x04,0x02,0x01,0x04,0x20,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    };
    char sha1_b64[29] = {0}, sha256_b64[29] = {0};
    char xml[1024];
    const unsigned char *template_ptr;
    CMS_ContentInfo *cms = NULL;
    CMS_SignerInfo *signer = NULL;
    BIO *key_bio = NULL, *cert_bio = NULL;
    EVP_PKEY *key = NULL;
    X509 *cert = NULL;
    int der_size = 0, result = 1;

    if (argc != 4) {
        fprintf(stderr, "usage: %s primary.cd alternate.cd output.blob\n", argv[0]);
        return 2;
    }
    if (read_file(argv[1], &sha1_cd, &sha1_size) || read_file(argv[2], &sha256_cd, &sha256_size)) {
        fprintf(stderr, "failed to read CodeDirectory input\n");
        goto done;
    }
    if (digest(EVP_sha1(), sha1_cd, sha1_size, sha1_hash, sizeof(sha1_hash)) ||
        digest(EVP_sha256(), sha256_cd, sha256_size, sha256_hash, sizeof(sha256_hash))) {
        fprintf(stderr, "failed to hash CodeDirectories\n");
        goto done;
    }
    memcpy(hashes_der + 11, sha1_hash, sizeof(sha1_hash));
    memcpy(hashes_der + 46, sha256_hash, sizeof(sha256_hash));
    base64(sha1_hash, sizeof(sha1_hash), sha1_b64);
    base64(sha256_hash, 20, sha256_b64);
    if (snprintf(xml, sizeof(xml),
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
        "<plist version=\"1.0\">\n<dict>\n\t<key>cdhashes</key>\n\t<array>\n"
        "\t\t<data>\n\t\t%s\n\t\t</data>\n\t\t<data>\n\t\t%s\n\t\t</data>\n"
        "\t</array>\n</dict>\n</plist>\n", sha1_b64, sha256_b64) >= (int)sizeof(xml)) {
        fprintf(stderr, "CDHashes plist overflow\n");
        goto done;
    }

    template_ptr = AppStoreSignatureBlob + 8;
    cms = d2i_CMS_ContentInfo(NULL, &template_ptr, AppStoreSignatureBlob_len - 8);
    key_bio = BIO_new_mem_buf(CAKey, (int)CAKeyLength);
    cert_bio = BIO_new_mem_buf(CACert, (int)CACertLength);
    if (!cms || !key_bio || !cert_bio) goto openssl_error;
    key = PEM_read_bio_PrivateKey(key_bio, NULL, NULL, NULL);
    cert = PEM_read_bio_X509(cert_bio, NULL, NULL, NULL);
    if (!key || !cert) goto openssl_error;
    signer = CMS_add1_signer(cms, cert, key, EVP_sha256(),
                             CMS_PARTIAL | CMS_REUSE_DIGEST | CMS_NOSMIMECAP);
    if (!signer) goto openssl_error;
    if (!CMS_signed_add1_attr_by_txt(signer, "1.2.840.113635.100.9.1",
                                     V_ASN1_OCTET_STRING, xml, (int)strlen(xml)) ||
        !CMS_signed_add1_attr_by_txt(signer, "1.2.840.113635.100.9.2",
                                     V_ASN1_SEQUENCE, hashes_der, sizeof(hashes_der)) ||
        !CMS_SignerInfo_sign(signer)) goto openssl_error;
    der_size = i2d_CMS_ContentInfo(cms, &der_output);
    if (der_size <= 0) goto openssl_error;
    if (write_blob(argv[3], der_output, der_size)) {
        fprintf(stderr, "failed to write CMS blob\n");
        goto done;
    }
    result = 0;
    goto done;

openssl_error:
    ERR_print_errors_fp(stderr);
done:
    OPENSSL_free(der_output);
    X509_free(cert);
    EVP_PKEY_free(key);
    BIO_free(cert_bio);
    BIO_free(key_bio);
    CMS_ContentInfo_free(cms);
    free(sha256_cd);
    free(sha1_cd);
    return result;
}
