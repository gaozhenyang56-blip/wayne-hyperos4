/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stddef.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "adapter.h"

_Static_assert(sizeof(struct ion_allocation_data) == 24, "fixed-width ION required");
_Static_assert(sizeof(struct dma_heap_allocation_data) == 24, "DMA heap UAPI size");
_Static_assert(offsetof(struct ion_allocation_data, fd) == 16, "ION fd offset");
_Static_assert(offsetof(struct dma_heap_allocation_data, fd) == 8, "heap fd offset");

int wayne_ion_system_plan(uint32_t profile, unsigned long command,
                         const struct ion_allocation_data *input,
                         struct dma_heap_allocation_data *output)
{
    struct dma_heap_allocation_data request = {0};
    if (!input || !output) return -EINVAL;
    if (profile != WAYNE_SOURCE_SYSTEM_PROFILE) return -EOPNOTSUPP;
    /* Legacy handle-based 32/64-bit ION, CUSTOM/SHARE/FREE are all rejected. */
    if (command != ION_IOC_ALLOC) return -ENOTTY;
    if (input->heap_id_mask != WAYNE_SOURCE_SYSTEM_MASK) return -EOPNOTSUPP;
    /* Mainline system heap is cached: no uncached/secure flag downgrading. */
    if (input->flags != ION_FLAG_CACHED) return -EOPNOTSUPP;
    if (input->unused || input->fd) return -EINVAL;
    if (!input->len || input->len > WAYNE_MAX_PROBE_BYTES) return -E2BIG;
    request.len = input->len;
    request.fd_flags = O_RDWR | O_CLOEXEC;
    request.heap_flags = 0;
    *output = request;
    return 0;
}

int wayne_ion_system_alloc_with_ops(uint32_t profile, unsigned long command,
                         const struct ion_allocation_data *input, int *output_fd,
                         const struct wayne_heap_ops *ops)
{
    struct dma_heap_allocation_data request;
    int result, heap;
    if (!output_fd) return -EINVAL;
    *output_fd = -1;
    if (!ops || !ops->open_heap || !ops->allocate || !ops->close_fd) return -EINVAL;
    result = wayne_ion_system_plan(profile, command, input, &request);
    if (result) return result;
    /* Heap control FD needs read/open/ioctl, not write. Buffer FD stays O_RDWR. */
    heap = ops->open_heap("/dev/dma_heap/system", O_RDONLY | O_CLOEXEC, ops->context);
    if (heap < 0) return heap;
    result = ops->allocate(heap, DMA_HEAP_IOCTL_ALLOC, &request, ops->context);
    ops->close_fd(heap, ops->context); /* Never retry close or close caller's buffer. */
    if (result < 0) return result;
    if (result != 0 || request.fd > INT_MAX) return -EIO;
    *output_fd = (int)request.fd;
    return 0;
}

static int system_open(const char *path, int flags, void *context)
{
    int fd; (void)context;
    fd = open(path, flags);
    return fd < 0 ? -errno : fd;
}
static int system_allocate(int fd, unsigned long command,
                           struct dma_heap_allocation_data *request, void *context)
{
    int result; (void)context;
    result = ioctl(fd, command, request);
    return result < 0 ? -errno : result;
}
static int system_close(int fd, void *context)
{
    (void)context;
    return close(fd);
}
int wayne_ion_system_alloc(uint32_t profile, unsigned long command,
                         const struct ion_allocation_data *input, int *output_fd)
{
    const struct wayne_heap_ops ops = {system_open, system_allocate, system_close, NULL};
    return wayne_ion_system_alloc_with_ops(profile, command, input, output_fd, &ops);
}
