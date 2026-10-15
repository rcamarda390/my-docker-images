/* Run against the installed libc, not a mock regex implementation. */
#define _GNU_SOURCE
#include <assert.h>
#include <locale.h>
#include <regex.h>
#include <stdio.h>
#include <sys/resource.h>
#include <unistd.h>

static void check(const char *pattern, const char *text, int flags, int expected)
{
    regex_t expression;
    regmatch_t matches[8];
    int result = regcomp(&expression, pattern, flags);
    assert(result == 0);
    alarm(5);
    result = regexec(&expression, text, 8, matches, 0);
    alarm(0);
    if (result != expected)
        fprintf(stderr, "regex result %d, expected %d: %s\n", result, expected, pattern);
    assert(result == expected);
    if (result == 0)
        assert(matches[0].rm_so >= 0 && matches[0].rm_eo >= matches[0].rm_so);
    regfree(&expression);
}

int main(int argc, char **argv)
{
    struct rlimit no_core = {0, 0};
    assert(setrlimit(RLIMIT_CORE, &no_core) == 0);
    /* Locales default to C and C.UTF-8; pass names as arguments for images
       that ship without C.UTF-8 (libc-bin purged). */
    const char *default_locales[] = {"C", "C.UTF-8"};
    const char **locales = argc > 1 ? (const char **)(argv + 1) : default_locales;
    unsigned int locale_count = argc > 1 ? (unsigned int)(argc - 1) : 2;
    for (unsigned int i = 0; i < locale_count; ++i) {
        assert(setlocale(LC_ALL, locales[i]) != NULL);
        /* Sourceware #24269 / CVE-2019-9192: baseline overflows its stack. */
        check("(|)(\\1\\1)*", "D", REG_EXTENDED, REG_ESPACE);
        /* GNU sed #34141 / CVE-2018-20796: distinct empty-backreference cycle. */
        check("\\(\\)\\(\\1\\(\\)\\1\\(\\)\\)*", "0", 0, REG_ESPACE);
        check("(a|b)+", "abba", REG_EXTENDED, 0);
        check("(ab)\\1", "abab", REG_EXTENDED, 0);
        check("(ab)\\1", "abac", REG_EXTENDED, REG_NOMATCH);
        check("(a*)\\1", "aaaa", REG_EXTENDED, 0);
        check("()\\1*\\1*", "D", REG_EXTENDED, 0);
        check("([[:alpha:]]+) ([[:digit:]]+)", "abc 123", REG_EXTENDED, 0);
        check("^a{2,4}$", "aaa", REG_EXTENDED, 0);
        check("^a{2,4}$", "aaaaa", REG_EXTENDED, REG_NOMATCH);
    }
    regex_t expression = {0};
    reg_syntax_t previous = re_set_syntax(RE_SYNTAX_POSIX_EXTENDED);
    assert(re_compile_pattern("(|)(\\1\\1)*", sizeof("(|)(\\1\\1)*") - 1, &expression) == NULL);
    assert(re_search(&expression, "D", 1, 0, 1, NULL) == -2);
    assert(re_match(&expression, "D", 1, 0, NULL) == -2);
    regfree(&expression);
    re_set_syntax(previous);
    puts("glibc recursive-backreference regressions passed");
    return 0;
}
