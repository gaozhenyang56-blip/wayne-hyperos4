/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include "adapter.h"

struct state {int opens, allocates, closes, open_error, allocation_error;};
static int fake_open(const char *path, int flags, void *context)
{
    struct state *s=context;s->opens++;
    assert(!strcmp(path,"/dev/dma_heap/system"));
    assert(flags==(O_RDONLY|O_CLOEXEC));return s->open_error ? s->open_error : 11;
}
static int fake_allocate(int fd, unsigned long cmd, struct dma_heap_allocation_data *r, void *context)
{
    struct state *s=context;s->allocates++;assert(fd==11 && cmd==DMA_HEAP_IOCTL_ALLOC);
    assert(r->len==4096 && r->fd_flags==(O_RDWR|O_CLOEXEC) && !r->heap_flags);
    if(s->allocation_error) return s->allocation_error;
    r->fd=42;
    return 0;
}
static int fake_close(int fd, void *context)
{struct state *s=context;s->closes++;assert(fd==11);return 0;}

int main(void)
{
    const uint32_t profile=WAYNE_SOURCE_SYSTEM_PROFILE;
    struct ion_allocation_data r={.len=4096,.heap_id_mask=WAYNE_SOURCE_SYSTEM_MASK,.flags=ION_FLAG_CACHED};
    struct dma_heap_allocation_data plan={0};struct state s={0};int fd=99;
    const struct wayne_heap_ops ops={fake_open,fake_allocate,fake_close,&s};
    assert(!wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan));assert(plan.len==4096);
    assert(wayne_ion_system_plan(0,ION_IOC_ALLOC,&r,&plan)==-EOPNOTSUPP);
    assert(wayne_ion_system_plan(profile,_IOC(_IOC_READ|_IOC_WRITE,'I',0,20),&r,&plan)==-ENOTTY);
    assert(wayne_ion_system_plan(profile,_IOC(_IOC_READ|_IOC_WRITE,'I',0,32),&r,&plan)==-ENOTTY);
    assert(wayne_ion_system_plan(profile,_IOC(_IOC_READ|_IOC_WRITE,'I',6,8),&r,&plan)==-ENOTTY);
    r.heap_id_mask=1u<<25;assert(wayne_ion_system_alloc_with_ops(profile,ION_IOC_ALLOC,&r,&fd,&ops)==-EOPNOTSUPP);
    assert(fd==-1 && !s.opens);r.heap_id_mask=WAYNE_SOURCE_SYSTEM_MASK;
    r.flags=0;assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan)==-EOPNOTSUPP);
    r.flags=ION_FLAG_CACHED|0x80000000u;assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan)==-EOPNOTSUPP);
    r.flags=ION_FLAG_CACHED;r.unused=1;assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan)==-EINVAL);
    r.unused=0;r.fd=7;assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan)==-EINVAL);r.fd=0;
    r.len=0;assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan)==-E2BIG);
    r.len=WAYNE_MAX_PROBE_BYTES+1;assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,&r,&plan)==-E2BIG);r.len=4096;
    assert(wayne_ion_system_plan(profile,ION_IOC_ALLOC,NULL,&plan)==-EINVAL);
    /* Policy/DAC refusal is propagated, never retried with broader access. */
    for (int denial = 0; denial < 2; denial++) {
        int error = denial ? -EPERM : -EACCES;
        struct state denied = {.open_error=error};
        struct wayne_heap_ops denied_ops = {fake_open,fake_allocate,fake_close,&denied};
        assert(wayne_ion_system_alloc_with_ops(profile,ION_IOC_ALLOC,&r,&fd,&denied_ops)==error);
        assert(fd==-1 && denied.opens==1 && !denied.allocates && !denied.closes);
        denied.open_error=0;denied.allocation_error=error;
        assert(wayne_ion_system_alloc_with_ops(profile,ION_IOC_ALLOC,&r,&fd,&denied_ops)==error);
        assert(fd==-1 && denied.opens==2 && denied.allocates==1 && denied.closes==1);
    }
    s.open_error=-ENOENT;assert(wayne_ion_system_alloc_with_ops(profile,ION_IOC_ALLOC,&r,&fd,&ops)==-ENOENT);
    assert(fd==-1 && !s.allocates && !s.closes);s.open_error=0;s.allocation_error=-ENOMEM;
    assert(wayne_ion_system_alloc_with_ops(profile,ION_IOC_ALLOC,&r,&fd,&ops)==-ENOMEM);
    assert(fd==-1 && s.closes==1);s.allocation_error=0;
    assert(!wayne_ion_system_alloc_with_ops(profile,ION_IOC_ALLOC,&r,&fd,&ops));assert(fd==42 && s.closes==2);
    puts("adapter positive translation and negative/FD ownership tests passed; mocked heap only");
    return 0;
}
