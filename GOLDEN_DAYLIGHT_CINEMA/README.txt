GOLDEN DAYLIGHT CINEMA
Standalone Apple Log 2 / Apple Wide Gamut -> Rec.709 SDR gamma 2.4

ONE 33 x 33 x 33 LUT. Creative rendering, not a neutral or Apple-supplied LUT.
The .cube expects normalized full-range Apple Log 2 RGB (not original Apple Log,
Rec.709, HLG, HDR display output, or ProRes RAW before decoding). Range expansion
from legal/video levels, if applicable, must be handled by your editing app.
No separate Log-to-709 conversion should be stacked before or after this LUT.
The target is SDR Rec.709 primaries and an ideal gamma 2.4 display, not HDR.

BLACKMAGIC CAMERA ON IPHONE (menu names vary by app version):
1. Download the .cube to Files. If using the ZIP, tap it in Files to extract it.
2. In Settings > Record > Color Space, select Apple Log 2 if available on your
   device and in your app version. This LUT is not for the original Apple Log.
3. In Settings > LUTs / LUT Selection, use Import LUT and pick the .cube in Files.
4. Select the imported LUT and enable Display LUT for monitoring. If available,
   leave Record LUT to Clip OFF to retain a clean Log recording for later grading.
5. Record and review a short test clip. Monitor exposure with waveform/zebras and
   set white balance deliberately. Avoid clipping. Adjust exposure and white
   balance BEFORE the LUT in post, in the appropriate log/linear domain.
6. In an editor, avoid automatic input conversion followed by this LUT: use an
   unmanaged path feeding Apple Log 2 directly to it. Tag output as Rec.709 SDR.

The exact UI and functionality have NOT been tested on a physical iPhone or in
Blackmagic Camera. Confirm behavior on your device before a paid shoot.
The gallery is GALLERY/index.html. It can be opened from the extracted folder;
local-file restrictions may vary by browser. PREVIEWS are synthetic comparative
images, NOT iPhone sensor footage; see VALIDATION_REPORT.txt for methods and
limitations. A LUT cannot restore clipped highlights or reliably fix exposure or
white balance in every scene.
