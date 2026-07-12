# Production Build and External Prerequisites

## Local verification

```bash
python -m compileall -q acli
python -m unittest discover -s tests -v
```

Docker Desktop/Engine is **optional** for end users and local developers. When Docker is unavailable, `run_isolated` automatically uses restricted native execution. Local Docker testing on every target operating system is **not required**. The repository includes a dedicated Linux CI job named **Docker sandbox contract** that builds the sandbox image and verifies its security contract automatically.

The CI contract checks:

- Read-only container root
- Dropped Linux capabilities
- `no-new-privileges`
- PID, CPU, and memory limits
- Network disabled
- Writable temporary filesystem
- Only the project workspace mounted writable

Windows and macOS CI jobs validate the native CLI, settings, packaging, and platform-specific code. The sandbox image itself is validated once in Linux container CI, where the isolation primitives execute natively.

The restricted native fallback is covered by cross-platform unit tests. Developers may still run an optional Docker check:

```bash
docker build -t devorbit-sandbox:latest -f packaging/Dockerfile.sandbox packaging
```

## Installers

`python packaging/build.py` creates an executable on the current OS. Native installers must be built on their target operating system. The included GitHub Actions workflow runs tests on Windows, macOS, and Linux, runs the Docker sandbox contract on Ubuntu, and uploads platform artifacts.

## Required outside this ZIP

- Apple Developer ID certificate and notarization credentials for signed macOS packages.
- Windows code-signing certificate for trusted installer reputation.
- GitHub repository Actions permissions and release secrets.
- Real NVIDIA/provider keys for live model and quota certification.
- GitHub OAuth application credentials for device-login distribution.

Unsigned artifacts are suitable for internal testing, not broad public distribution.
