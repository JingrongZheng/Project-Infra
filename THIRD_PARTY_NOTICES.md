# Third-party notices

Project Infra's own source code and PI vector mark are provided under the root MIT LICENSE. Third-party components retain their original licenses; the MIT license does not replace them.

## Bundled Python runtime distributions

The Windows and Linux portable bundles include the CPython runtime used by their respective build environments. The current Windows release uses CPython 3.12.7. Each release builder must verify the Linux build's Python and dynamically collected library versions before publishing. Retained license texts include:

| Component | License text |
|---|---|
| Python | licenses/Python.txt |
| PyInstaller bootloader and bundling exception | licenses/PyInstaller.txt |
| Tcl / Tk | licenses/Tcl-Tk.txt |
| OpenSSL | licenses/OpenSSL.txt |
| libffi | licenses/libffi.txt |
| mpdecimal | licenses/mpdecimal.txt |
| bzip2 | licenses/bzip2.txt |
| XZ / liblzma | licenses/xz.txt |
| zlib | licenses/zlib.txt |

Microsoft runtime DLLs originate from the Windows build runtime's redistributable components and retain their applicable Microsoft terms. The Linux bundle intentionally uses the target system's X11 client libraries and libuuid instead of redistributing them; these are part of the documented base-system boundary. Dependency versions, collected binaries and notices must be reviewed when changing either build environment.

## Installer and localization

The installer is built with Inno Setup: https://jrsoftware.org/
The simplified Chinese messages file installer/ChineseSimplified.isl is provided by the Inno Setup translations project and retains its original maintainer and source notices: https://jrsoftware.org/files/istrans/

The previously explored game-derived rose is not a distributed asset. Current builds explicitly include only the PI SVG, PNG and ICO files.
