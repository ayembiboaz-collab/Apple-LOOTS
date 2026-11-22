# Checkpoint: candidate NOT READY FOR REVIEW OR USE

This checkpoint preserves research, a float64 prototype and reproducible numerical tests, not the requested finished project. The `.cube` under build/ is an experimental intermediate, not an approved or final deliverable.

## Results that block release

* The 50,000 uniformly random full-domain input test (seed 1717) yields mean / 99th percentile / maximum ΔE00 of approximately 0.399 / 6.048 / 19.941 for trilinear and 0.299 / 4.729 / 19.977 for tetrahedral. This distribution includes impossible and unusual camera values; no inference about prevalence in actual footage is justified, but the errors are too high to ignore.
* On 4097 sampled input steps with trilinear interpolation, the yellow, cyan and magenta input-code ramps have 68, 22 and 7 luminance reversals respectively. This is a failed smoothness check. The blue ramp is entirely black because the selected input-code ray fixes the other two Apple Log channels at code 0, encoding negative signal values, and the Apple Wide Gamut blue primary has a negative Y coordinate; that test therefore cannot demonstrate behaviour on physically plausible blue objects. Use nonnegative scene-linear, exposure-scaled colours for a future test.
* Simulated independent 0.001-sigma log-code noise gives output-code sigma gains of up to roughly 3.56 in the tested patches. This is neither calibrated sensor noise nor proof of a capped shadow-noise gain. The candidate does not meet the requested shadow-noise criterion.
* The experimental tone mapping uses an OKLab-lightness proxy and a soft chroma-boundary compression. The skin-hue parameters are not numerically validated against a vectorscope skin line. No scene-specific test supports claims of attractive or reference-grade imagery.

## Performed

* Reparsed 35,937 rows from the candidate .cube, verified finite output and [0,1] range and tested the header; recorded its SHA-256 in candidate-validation.json.
* Checked the Apple Log curve and AWG-to-ACES AP0 D65-to-D60 Bradford transform against OpenColorIO's published sample; largest channel difference 4.49e-7. Checked the analytic 18% grey output against the explicitly specified 1/2.4 power.
* Measured full-domain trilinear and tetrahedral interpolation ΔE00, neutral and primary/secondary input-code ramps, 8/10-bit output code counts, a synthetic neutral ±4-stop ladder and the synthetic noise perturbations. Quantized code counts do not prove an absence of banding; input-code primary ramps are not exposure-normalised scene primaries.

## Still required

Acquire eight individually licence-verified, real, sufficiently high-resolution photographs (preferably source raws) covering the requested categories. Network restrictions prevented direct downloads from original image hosts. The image-search service returned low-resolution previews, some already heavily graded; none have been represented as valid proof or committed. Simulate Apple Log 2 from those photos and document assumptions, render the delivered cube independently, visually iterate, complete every requested diagnostic and per-scene clipping / hue / skin / exposure test, build the gallery and contact sheet, package and hash-verify the ZIP, test responsive/touch interaction, then commit/push and verify remote downloads before presenting the finished work for review. No actual iPhone 17 Pro or Blackmagic Camera testing has been performed. No PR should be created without explicit user approval.

## Second iteration (supersedes the earlier candidate figures)

Applied a smooth scene-linear pre-gamut compression plus stronger highlight chroma thinning. Re-ran the tests. Uniform full-domain trilinear mean / p99 / max ΔE00: 0.331 / 5.108 / 25.503; tetrahedral: 0.236 / 3.736 / 27.931. Maximum error is worse, largely in imaginary, negative-Y triples. Input-code-ramp luminance reversals: yellow 14, others 0; the blue ramp caveat above remains. At the +4-stop neutral ladder point, inter-channel spread decreased from approximately 0.0211 to 0.0033. These are still not sufficient to establish quality or safety for real camera footage. Full-domain maxima and failures are retained, not concealed.
