# Static Folder Contents
# Contains tracking pixel image for beacon tracking

This folder contains static assets used by the honeypot:

- **tracking_pixel.png** - 1x1 transparent PNG used for tracking when bait files are opened
- Future: Logo images, CSS files, etc.

The tracking pixel is embedded in generated PDF and Excel files. When the file is opened, it attempts to load the pixel from the honeypot server, triggering a beacon activation alert.
