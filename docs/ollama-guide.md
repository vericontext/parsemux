# Ollama local VLM guide

Use Ollama when you want free, local image description for extracted document images.

## Install Ollama

1. Install Ollama from <https://ollama.com/download>.
2. Start the Ollama service on your machine.
3. Pull the default local vision model used by parsemux:

```bash
ollama pull qwen2.5vl:7b
```

Parsemux defaults to `qwen2.5vl:7b` for local image description.

## Run parsemux with local image description

When you do not provide `--vlm-key` or `--llm-key`, parsemux auto-detects the VLM provider as Ollama.

```bash
parsemux parse doc.pdf --extract-images --describe-images
```

This flow:

- extracts images from the document
- sends them to the local Ollama server at `http://localhost:11434`
- writes image descriptions back into the parse result

You can also set the provider explicitly:

```bash
parsemux parse doc.pdf --extract-images --describe-images --vlm-provider ollama
```

## Performance expectations

Ollama is the zero-cost option, but it trades speed for privacy and local control.

- Speed: slower than hosted APIs, especially on CPU-only machines
- Quality: good enough for many document images, charts, and screenshots, but usually below top cloud vision models
- Privacy: best option when documents must stay on your machine
- Cost: `0.0` direct API cost inside parsemux

For best results:

- use a machine with a capable GPU if available
- keep document batches small when testing locally
- expect longer runtimes for image-heavy PDFs
