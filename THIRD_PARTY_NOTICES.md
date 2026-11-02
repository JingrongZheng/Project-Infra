# Third-party notices

Project Infra's own source code and PI vector mark are provided under the root MIT LICENSE. Third-party components retain their original licenses; the MIT license does not replace them.

## Windows runtime distribution

The current Windows bundle includes CPython 3.12.7 and its runtime libraries. License texts copied from the build runtime are retained in licenses/:

| Component | License text |
|---|---|
| Python | licenses/Python.txt |
| PyInstaller bootloader and bundling exception | licenses/PyInstaller.txt |
| Tcl / Tk | licenses/Tcl-Tk.txt |
| OpenSSL | licenses/OpenSSL.txt |
| libffi | licenses/libffi.txt |
| bzip2 | licenses/bzip2.txt |
| XZ / liblzma | licenses/xz.txt |
| zlib | licenses/zlib.txt |

Microsoft runtime DLLs originate from the build runtime's Windows redistributable components and retain their applicable Microsoft terms. Dependency versions and notices must be reviewed when changing the build environment.

## Installer and localization

The installer is built with Inno Setup: https://jrsoftware.org/
The simplified Chinese messages file installer/ChineseSimplified.isl is provided by the Inno Setup translations project and retains its original maintainer and source notices: https://jrsoftware.org/files/istrans/

The previously explored game-derived rose is not a distributed asset. Current builds explicitly include only the PI SVG, PNG and ICO files.
