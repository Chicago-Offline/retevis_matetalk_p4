# ReTevis MateTalk P4

This repository stores the vendor-supplied programming software and firmware for the ReTevis MateTalk P4 radio. It is primarily an archive and reference repository rather than a full source tree.

## Included files

- `cps/P4-Programming-Software.zip` — Windows programming software for the radio.
- `firmware/P4-64-Firmware.zip` — firmware image for the P4 radio.

## Related research

There is upstream reverse-engineering work for this platform, including the p64tool project, which documents codeplug structure and related details. The key takeaway from the current issue is that calibration data does not appear to live in the codeplug itself.

## Notes

- This repository does not contain a custom firmware build or a full reverse-engineering implementation.
- Use the programming software and firmware only with compatible hardware.
- Back up radio settings before flashing or reprogramming.

## Project purpose

This repo serves as a minimal archive for the official software and firmware needed to work with the MateTalk P4, while recording the fact that more detailed reverse-engineering work exists upstream.
