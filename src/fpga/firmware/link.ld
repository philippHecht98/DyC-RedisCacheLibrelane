/* Linker script for 64 KB TCM at 0x0000_0000 */

MEMORY
{
    TCM (rwx) : ORIGIN = 0x00000000, LENGTH = 64K
}

ENTRY(_start)

SECTIONS
{
    .text : {
        *(.text.init)
        *(.text*)
    } > TCM

    .rodata : {
        *(.rodata*)
    } > TCM

    .data : {
        *(.data*)
    } > TCM

    .bss : {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        _bss_end = .;
    } > TCM

    /* Stack grows downward from top of TCM */
    _stack_top = ORIGIN(TCM) + LENGTH(TCM);
}
