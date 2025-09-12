## Encoder Interrupt Configuration

- **Single‐channel IRQ**  
  Only Channel A is attached to an interrupt (IRQ). This keeps the interrupt‐service routine (ISR) small and fast.

- **Reduced interrupt load**  
  With a 13 PPR encoder and full quadrature decoding (4 edges per pulse) at 300 RPM:  
  `13 pulses/rev × 4 edges × (300/60) = 260 interrupts/second`  
  By limiting IRQs to Channel A only, we cut that overhead in half—significantly reducing CPU time spent in the ISR.

- **Minimal ISR complexity**  
  With Single‐channel IRQ, the ISR simply:  
  1. Reads the state of Channel B  
  2. Increments or decrements a single counter  

  This approach is easy to verify, yields predictable execution times, and prevents the microcontroller from being overwhelmed at high speeds.
