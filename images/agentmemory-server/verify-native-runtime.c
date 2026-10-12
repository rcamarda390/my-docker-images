/* verify-native-runtime.c: exercise the actual runtime libc and zlib. */
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <locale.h>
#include <monetary.h>
#include <resolv.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <zlib.h>

int main(void)
{
    /* Reuse Gnosis's CVE-2026-19499 guard-page check against actual libc. */
    const size_t page_size = (size_t)sysconf(_SC_PAGESIZE);
    char *pages = mmap(NULL, page_size * 2, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(pages != MAP_FAILED);
    assert(mprotect(pages + page_size, page_size, PROT_NONE) == 0);
    char *output = pages + page_size - 100;
    locale_t locale = newlocale(LC_MONETARY_MASK, "C", NULL);
    assert(locale != (locale_t)0);
    errno = 0;
    assert(strfmon(output, 100, "%100n", 1.23) == -1 && errno == E2BIG);
    errno = 0;
    assert(strfmon_l(output, 100, locale, "%100n", 1.23) == -1 && errno == E2BIG);
    assert(strfmon_l(output, 100, locale, "%.2n", 1.23) == 4);
    assert(strcmp(output, "1.23") == 0);
    freelocale(locale);
    assert(munmap(pages, page_size * 2) == 0);

    /* CVE-2026-95619 affects non-posix_memalign implementations. Exercise
       the installed C++ ABI without letting a throwing ABI cross into C. */
    void *cpp = dlopen("libstdc++.so.6", RTLD_NOW);
    assert(cpp != NULL);
    void *(*allocate)(size_t, size_t, const void *) =
        dlsym(cpp, "_ZnwmSt11align_val_tRKSt9nothrow_t");
    void (*release)(void *, size_t) = dlsym(cpp, "_ZdlPvSt11align_val_t");
    void *nothrow = dlsym(cpp, "_ZSt7nothrow");
    assert(allocate != NULL && release != NULL && nothrow != NULL);
    const size_t cases[][2] = {
        {SIZE_MAX - 8, 32}, {SIZE_MAX, 8}, {SIZE_MAX, 32},
        {SIZE_MAX, 1024}, {SIZE_MAX, 65536}, {SIZE_MAX - 1, 16},
        {SIZE_MAX - 1025, 1024}, {SIZE_MAX - 1024, 1024},
        {SIZE_MAX - 65536, 65536},
    };
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        assert(allocate(cases[i][0], cases[i][1], nothrow) == NULL);
    }
    void *ordinary = allocate(64, 32, nothrow);
    assert(ordinary != NULL && (uintptr_t)ordinary % 32 == 0);
    release(ordinary, 32);
    assert(dlclose(cpp) == 0);

    /* Previously an oversized LOCALDOMAIN could abort in resolver setup. */
    char domain[4096];
    memset(domain, 'a', sizeof domain - 1);
    domain[sizeof domain - 1] = '\0';
    assert(setenv("LOCALDOMAIN", domain, 1) == 0);
    assert(res_init() == 0);
    strcpy(domain, "example.org ");
    memset(domain + 12, 'a', sizeof domain - 13);
    domain[sizeof domain - 1] = '\0';
    assert(setenv("LOCALDOMAIN", domain, 1) == 0);
    assert(res_init() == 0);

    assert(strcmp(zlibVersion(), "1.3.2") == 0);
    const unsigned char input[] = "AgentMemory runtime compression";
    unsigned char compressed[128], restored[128];
    uLongf compressed_size = sizeof compressed, restored_size = sizeof restored;
    assert(compress(compressed, &compressed_size, input, sizeof input) == Z_OK);
    assert(uncompress(restored, &restored_size, compressed, compressed_size) == Z_OK);
    assert(restored_size == sizeof input);
    assert(memcmp(input, restored, sizeof input) == 0);
    return 0;
}
