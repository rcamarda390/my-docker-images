/* verify-glibc-normalize.c: regression checks for the secure-loader backport.
   Check the upstream normalizer against representative upstream test cases,
   with each input immediately before and after an inaccessible guard page. */
#define _GNU_SOURCE
#include <assert.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <dl-path-normalize.h>

int
main (void)
{
  const char *cases[][2] = {
    {"", ""}, {"/", "/"}, {"////", "/"}, {"/.", "/"},
    {"/..", "/"}, {"/../a", "/a"}, {"/a/../b", "/b"},
    {"/a/b/../../c", "/c"}, {"/a/../../b", "/b"},
    {"/usr/lib/..//lib64/", "/usr/lib64"},
    {"/tmp/a/b/sub/../../../../../usr/lib", "/usr/lib"},
    {"/a/...", "/a/..."}, {".", ""}, {"..", ".."},
    {"../..", "../.."}, {"a/..", ""}, {"a/../b", "b"},
    {"a/b/../../..", ".."}, {"a/../../b", "../b"},
    {"../../a/..", "../.."}, {"./a//b/", "a/b"}
  };
  long page = sysconf (_SC_PAGESIZE);
  assert (page > 0);
  char *area = mmap (NULL, 3 * page, PROT_NONE,
                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  assert (area != MAP_FAILED);
  assert (mprotect (area + page, page, PROT_READ | PROT_WRITE) == 0);
  for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i)
    for (int before = 0; before < 2; ++before)
      {
        size_t size = strlen (cases[i][0]) + 1;
        char *input = before ? area + page : area + 2 * page - size;
        memcpy (input, cases[i][0], size);
        size_t len = _dl_normalize_path (input);
        assert (len == strlen (cases[i][1]));
        assert (strcmp (input, cases[i][1]) == 0);
      }
  assert (munmap (area, 3 * page) == 0);
  return 0;
}
