# Repository Guidelines

## Project Structure & Module Organization

- `LaTeXOCR/`: macOS app source (Swift/SwiftUI + AppKit), including `ContentView.swift`, OCR logic in `IdentifyProcess.swift`, and rendering in `KaTexView.swift`.
- `LaTeXOCR/Assets.xcassets` and `LaTeXOCR/Assets/`: app images and bundled assets.
- `LaTeXOCRTests/`: unit tests (XCTest).
- `LaTeXOCRUITests/`: UI tests (XCTest).
- `LaTeXOCR.xcodeproj/`: Xcode project and schemes.
- Root `test.py`, `test.html`, `d.txt`: ad-hoc experiments; avoid depending on these for production behavior.

## Build, Test, and Development Commands

- Open in Xcode: `open LaTeXOCR.xcodeproj`
- Build (Debug): `xcodebuild -project LaTeXOCR.xcodeproj -scheme LaTeXOCR -configuration Debug build`
- Run locally: use Xcode “Run” (`⌘R`) for the macOS target.
- Tests (unit + UI): `xcodebuild -project LaTeXOCR.xcodeproj -scheme LaTeXOCR -destination 'platform=macOS' test`
- Clean: `xcodebuild -project LaTeXOCR.xcodeproj -scheme LaTeXOCR clean`

## Coding Style & Naming Conventions

- Swift: 4-space indentation, prefer Swift API Design Guidelines, and keep types `UpperCamelCase` and members `lowerCamelCase`.
- Keep SwiftUI views small and move side-effect/network logic into dedicated types (e.g., `IdentifyProcess`).
- No formatter/linter is configured in-repo; use Xcode formatting and keep diffs minimal and focused.

## Testing Guidelines

- Framework: XCTest (`LaTeXOCRTests/`, `LaTeXOCRUITests/`).
- Name tests `test…` and keep them deterministic; avoid real network calls (mock OCR/API responses where possible).

## Commit & Pull Request Guidelines

- Commit messages are currently mixed (plain summaries and occasional `feat:`). Prefer concise, imperative summaries; optionally follow Conventional Commits (`feat:`, `fix:`, `chore:`).
- PRs should include: what/why, how you tested (commands or Xcode steps), and screenshots for UI changes.

## Security & Configuration Tips

- Do not commit secrets (API keys, campus login credentials). Use local `.xcconfig` (gitignored), build settings, or Keychain-based storage for sensitive values.
