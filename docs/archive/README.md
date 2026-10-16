# Historical records

This directory preserves the original design and local acceptance evidence.
These are archival records, **not current installation or calibration instructions**.
Some documents and captured messages remain in Chinese to preserve the original
wording. Current documentation, source messages, and the active board are English.

| Record | Location |
| --- | --- |
| README before the English rewrite | [Original README](legacy/README.original.zh.md) |
| Original research and v1 report | [Research](legacy/docs/research.md), [report](legacy/docs/report.md) |
| v1.1 design and failed historical thresholds | [Initial report](legacy/docs/v1_1/report.md), [review 4](legacy/docs/v1_1/review4/report.md) |
| Last historical acceptance decision | [Review 5](legacy/docs/v1_1/review5/report.md) |
| Original v1.1.0 specification | [Specification](legacy/spec/board_v1_1.json) |
| Superseded v1 board | [Original archive](legacy/superseded/README.md) |

**Do not print v1.** It had a 2.25 mm white margin and depended on an additional
corner-refinement selection rule. Current geometry uses a 5.5 mm margin and the
standard OpenCV detection path. Use the [active PDF](https://github.com/5o1/calib_board/releases/download/v1.1.1/board_v1_1_A3.pdf).

The historical term “release completed” describes a private workstation copy,
not a public repository release or a real-camera validation. Host-specific copy
records remain historical deployment evidence and are not part of setup.
Earlier files retain their original paths inside hash manifests; those hashes
identify the then-current artifacts, not the rewritten source or v1.1.1 PDF.
Some original links describe paths in the old checkout and may no longer resolve.
Machine-readable values and raw logs have not been translated or reclassified.

Generated historical PDFs are kept locally under ignored `build/archive/`, outside
the source repository. Original records retain old output paths as historical text.
