# DMTAP — formal Internet-Draft (LaTeX)

This builds the DMTAP specification as a **formal, typeset Internet-Draft PDF**.

## Why "draft", not an RFC number

You never self-assign an RFC number. A proposal's proper identity is an **Internet-Draft**
named `draft-<author>-<name>-<version>` — here **`draft-paruk-dmtap-00`**, with an *Intended
status* (Experimental) and a six-month *Expires* date. An RFC number is assigned only if/when a
standards body publishes it. The cover, "Status of This Memo," and running heads reflect this
correctly.

## Build

Requires **pandoc** (Markdown → LaTeX) and a LaTeX engine (**tectonic** recommended; xelatex,
lualatex, or pdflatex also work):

```sh
./build.sh          # converts ../NN-*.md → body/*.tex, then compiles dmtap.pdf
```

Output: `dmtap.pdf` (~51 pp).

## Files

| File | Role |
|------|------|
| `dmtap.tex` | Master document — Internet-Draft front matter + `\input`s the section bodies |
| `preamble.tex` | Formal styling (Envoir palette, section design, code boxes, running heads) |
| `build.sh` | Converts the spec markdown via pandoc and compiles |
| `body/*.tex` | Generated per-section LaTeX (not committed; produced by `build.sh`) |
| `dmtap.pdf` | The built draft (committed for convenience) |

The Markdown in `../` remains the canonical source; this is a typeset rendering of it. For the
*authentic* IETF submission format, the same content can also be run through `kramdown-rfc` /
`xml2rfc` to produce the canonical RFC/I-D appearance.
