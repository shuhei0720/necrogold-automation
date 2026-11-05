/* LoopCtrl PRF-CTR acceleration. Cryptographic primitives remain OpenSSL's.
   No libc link, SIMD, private OpenSSL structures or wire-protocol changes.
   The Python adapter supplies public OpenSSL function addresses. */
typedef unsigned char Byte;
typedef __SIZE_TYPE__ Size;
typedef struct {
    void *(*create)(void);
    void (*destroy)(void *);
    int (*init)(void *, const void *, int, const void *, void *);
    int (*update)(void *, const Byte *, Size);
    int (*final)(void *, Byte *, unsigned int *);
    int (*copy)(void *, const void *);
} API;

int prf_xor(const API *api, const void *digest, const Byte *key, int keylen,
            const Byte *nonce, Size nonce_len, const Byte *src, Byte *dst, Size len) {
    if (!api || !digest || keylen < 0) return 0;
    void *base = api->create(), *work = api->create();
    int ok = 0;
    Byte block[32], counter[4];
    if (!base || !work) goto done;
    if (!api->init(base, key, keylen, digest, (void *)0) ||
        !api->update(base, nonce, nonce_len)) goto done;
    for (Size at = 0; at < len;) {
        unsigned int number = (unsigned int)(at / 32), count = 0;
        counter[0] = (Byte)(number >> 24); counter[1] = (Byte)(number >> 16);
        counter[2] = (Byte)(number >> 8); counter[3] = (Byte)number;
        if (!api->copy(work, base) || !api->update(work, counter, 4) ||
            !api->final(work, block, &count) || count != 32) goto done;
        Size take = len - at; if (take > 32) take = 32;
        for (Size i = 0; i < take; ++i) dst[at+i] = src[at+i] ^ block[i];
        at += take;
    }
    ok = 1;
done:
    if (work) api->destroy(work);
    if (base) api->destroy(base);
    /* Do not leave the last key-stream block in the stack frame. */
    for (volatile Byte *p = block; p < block+32; ++p) *p = 0;
    return ok;
}
