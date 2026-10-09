/* SPDX-License-Identifier: MIT */
#ifndef WAYNE_DMA_HEAP_ADAPTER_H
#define WAYNE_DMA_HEAP_ADAPTER_H
#include <stdint.h>
#include "ion-lineage.h"
#include "dma-heap.h"

/* Source-owned protocol. This is NOT a Qualcomm/OEM heap-ID mapping. */
#define WAYNE_SOURCE_SYSTEM_PROFILE UINT32_C(0x574e6601)
#define WAYNE_SOURCE_SYSTEM_MASK UINT32_C(1)
#define WAYNE_MAX_PROBE_BYTES UINT64_C(16777216)

struct wayne_heap_ops {
    int (*open_heap)(const char *path, int flags, void *context);
    int (*allocate)(int heap_fd, unsigned long command,
                    struct dma_heap_allocation_data *request, void *context);
    int (*close_fd)(int fd, void *context);
    void *context;
};

/* Negative errno on failure. Only fixed-width, cached, source-owned requests. */
int wayne_ion_system_plan(uint32_t profile, unsigned long command,
                         const struct ion_allocation_data *input,
                         struct dma_heap_allocation_data *output);
int wayne_ion_system_alloc_with_ops(uint32_t profile, unsigned long command,
                         const struct ion_allocation_data *input, int *output_fd,
                         const struct wayne_heap_ops *ops);
int wayne_ion_system_alloc(uint32_t profile, unsigned long command,
                         const struct ion_allocation_data *input, int *output_fd);
#endif
