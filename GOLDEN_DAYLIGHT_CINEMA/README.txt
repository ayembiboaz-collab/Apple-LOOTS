GOLDEN DAYLIGHT CINEMA
======================
One 33x33x33 creative conversion LUT: Apple Log 2 / Apple Wide Gamut input to Rec.709 SDR, display gamma 2.4 output. Not for original Apple Log/Rec.2020 or already-converted Rec.709. Do not stack another Log-to-709 conversion on it. Standard normalized 0–1 code values are expected; allow the editing app to correctly interpret full/video range first. A LUT cannot fix clipped highlights, white balance, or exposure, and extreme colours may be compressed.

BLACKMAGIC CAMERA FOR IPHONE
1. Save the .cube to Files (or unzip the full package in Files).
2. In Blackmagic Camera select Apple Log 2 in recording colour space if offered on your device. Names and availability depend on app/iOS version.
3. In LUT settings / LUT manager choose Import and select the .cube in Files. Select the imported LUT for monitoring and set its colour space tag to Rec.709 if offered.
4. Use display-only monitoring for clean Log recording; leave Record LUT to Clip off unless a baked-in look is specifically desired. Apply the same LUT ONCE to the clean Log in an editor with colour management/conversions disabled for that clip. Adjust exposure and white balance before the LUT when necessary.

These are guidance based on published third-party instructions, not tested on a physical iPhone or Blackmagic Camera. Menu names may change. Verify monitoring versus recording behaviour in your version before an important shoot. Reference: https://absoluts-store.com/blogs/blog/blackmagic-camera-iphone-settings-luts

PREVIEWS
Open GALLERY/index.html, or see PREVIEWS and CONTACT_SHEET. The images are AI-generated simulated scenes, not photographs from a phone. BEFORE is a neutral SDR reference derived from the same source and simulated exposure; AFTER comes from the actual .cube. The images are 8-bit PNG for viewing and do not demonstrate captured dynamic range or sensor colour. See VALIDATION_REPORT.txt for methodology and limitations.

GALLERY uses relative local links and requires JavaScript for sliders and modal viewing. Safari downloads/embedded preview behaviour was not tested on iPhone. If the embedded preview blocks downloads, use the GitHub direct file links instead.
