/*
 *  Bare-metal main – LED blink + UART "Hello, Arty A7!\n"
 *
 *  Peripheral base: 0x8000_0000  (mapped via AXI master port)
 *    +0x00  GPIO_LED     (W)  – led[3:0]
 *    +0x04  UART_TX      (W)  – byte to transmit
 *    +0x08  UART_STATUS  (R)  – bit 0 = tx_busy
 */

#include <stdint.h>

#define GPIO_LED      (*(volatile uint32_t *)0x80000000)
#define UART_TX       (*(volatile uint32_t *)0x80000004)
#define UART_STATUS   (*(volatile uint32_t *)0x80000008)

static void uart_putc(char c)
{
    /* Wait until TX is idle */
    while (UART_STATUS & 1)
        ;
    UART_TX = (uint32_t)c;
}

static void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

static void delay(volatile uint32_t count)
{
    while (count--)
        ;
}

void main(void)
{
    uart_puts("Hello, Arty A7!\r\n");

    uint8_t pattern = 0;
    while (1) {
        GPIO_LED = pattern & 0x0F;
        pattern++;
        delay(5000000);   /* ~50 ms @ 100 MHz  */
    }
}
