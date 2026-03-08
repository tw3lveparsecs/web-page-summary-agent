# Planning Guide

A sophisticated frontend interface for a Python-based web scraping agent that extracts and summarises web content using Microsoft Foundry, supporting both Entra ID and API key authentication methods.

**Experience Qualities**: 
1. **Professional** - Clean, corporate aesthetic that feels enterprise-ready and trustworthy for handling authenticated API operations
2. **Efficient** - Streamlined workflow from authentication through configuration to result delivery with minimal friction
3. **Technical** - Code-aware interface with syntax highlighting and structured data presentation for developer users

**Complexity Level**: Light Application (multiple features with basic state)
The application handles authentication configuration, text editing, URL list management, and result display. While it connects to a Python backend agent, the frontend itself maintains configuration state and displays results without complex multi-view navigation or advanced data relationships.

## Essential Features

**Authentication Configuration**
- Functionality: Toggle between Entra ID (with Managed Identity or Service Principal sub-options) and API key authentication modes, store credentials securely in session
- Purpose: Enable flexible authentication to Microsoft Foundry based on user's access method and deployment context
- Trigger: User selects auth method on initial load or via settings
- Progression: Select auth method (Entra/API Key) → If Entra, select auth type (Managed Identity/Service Principal) → Enter credentials (client ID only for MI; tenant/client/secret for SP; OR API key) → Validate → Store in state → Enable agent execution
- Success criteria: Credentials persist during session, toggle seamlessly switches modes, UI clearly indicates current auth state and type, Managed Identity option simplifies credential management

**System Prompt Editor**
- Functionality: Multi-line text editor for crafting the system prompt sent to Foundry
- Purpose: Allow users to customise how the AI agent summarises content
- Trigger: User clicks on system prompt editor area
- Progression: Click editor → Type/paste prompt text → Auto-save to state → Preview available for execution
- Success criteria: Text persists during session, supports multi-paragraph content, clear visual indication of content presence

**URL List Manager**
- Functionality: Text area for entering multiple URLs (one per line) to be scraped and summarized
- Purpose: Define target web pages for content extraction
- Trigger: User clicks on URL input area
- Progression: Click input → Enter URLs (one per line) → Auto-save to state → Validate URL format → Display count → Ready for execution
- Success criteria: Handles multiple URLs cleanly, shows URL count, persists list during session, provides helpful placeholder text

**Agent Execution Control**
- Functionality: Trigger Python agent in background with current configuration, show progress, handle errors
- Purpose: Execute the web scraping and summarization workflow
- Trigger: User clicks "Run Agent" button with valid auth and URLs
- Progression: Click run → Validate inputs → Disable controls → Show loading state → Execute agent → Stream results → Re-enable controls
- Success criteria: Clear loading indicator, error handling with helpful messages, prevents duplicate runs, shows execution status

**Result Display System**
- Functionality: Display summarised content with toggle between console output and formatted markdown view
- Purpose: Present results in user's preferred format matching the Python CLI options
- Trigger: Agent completes execution successfully
- Progression: Agent finishes → Parse results → Display in console view (default) → User toggles to markdown view → Download option available
- Success criteria: Results clearly formatted, toggle works instantly, download preserves formatting, results persist until next run

**Theme Toggle**
- Functionality: Switch between light and dark colour schemes with persistent preference
- Purpose: Allow users to customise visual appearance based on preference or environment
- Trigger: User clicks theme toggle button in header
- Progression: Click toggle → Theme switches instantly → Preference saved → Persists across sessions
- Success criteria: Smooth transition between themes, all components adapt correctly, preference persists

## Edge Case Handling

- **Invalid URLs**: Validate URL format client-side, show inline errors for malformed entries, prevent execution with invalid URLs
- **Authentication Failures**: Display clear error messages for invalid credentials, prompt re-entry, maintain other form state
- **Agent Timeout**: Show timeout message after reasonable period, allow cancellation, preserve configuration for retry
- **Empty Results**: Handle cases where agent returns no content with helpful message, suggest troubleshooting steps
- **Network Errors**: Graceful degradation with error display, retry option, maintain user's work-in-progress
- **Large URL Lists**: Support scrolling in URL manager, show count indicator, warn if list seems unusually large

## Design Direction

The design should evoke a sense of technical precision and professional capability - feeling like a developer tool rather than a consumer application. It should communicate reliability, clarity, and efficiency through structured layouts, code-aware typography, and subtle technical aesthetics. The interface should feel like a sophisticated command center for web scraping operations.

## Color Selection

A technical, developer-focused colour scheme supporting both light and dark modes with seamless transitions.

**Dark Mode (Default):**
- **Primary Color**: Deep navy blue (oklch(0.25 0.08 250)) - Represents technical depth, professionalism, and Microsoft's enterprise ecosystem
- **Secondary Colors**: Slate grey backgrounds (oklch(0.18 0.02 250)) for code editors and input areas; Lighter slate (oklch(0.35 0.03 250)) for secondary surfaces
- **Accent Color**: Electric cyan (oklch(0.75 0.15 200)) - Highlights active states, CTAs, and success indicators with a digital, technical feel
- **Foreground/Background Pairings**: 
  - Primary navy (oklch(0.25 0.08 250)): White text (oklch(0.98 0 0)) - Ratio 11.2:1 ✓
  - Background dark (oklch(0.18 0.02 250)): Light grey text (oklch(0.88 0.02 250)) - Ratio 12.8:1 ✓
  - Accent cyan (oklch(0.75 0.15 200)): Dark navy text (oklch(0.15 0.05 250)) - Ratio 9.4:1 ✓
  - Secondary slate (oklch(0.35 0.03 250)): White text (oklch(0.98 0 0)) - Ratio 8.6:1 ✓

**Light Mode:**
- **Primary Color**: Medium navy blue (oklch(0.35 0.10 250)) - Maintains technical authority in lighter environment
- **Secondary Colors**: Pale grey backgrounds (oklch(0.98 0 0)) for main surface; Mid-tone grey (oklch(0.92 0.01 250)) for secondary surfaces
- **Accent Color**: Vibrant teal (oklch(0.60 0.18 200)) - Energetic highlight colour for interactive elements
- **Foreground/Background Pairings**:
  - Primary navy (oklch(0.35 0.10 250)): White text (oklch(0.98 0 0)) - Ratio 6.8:1 ✓
  - Background light (oklch(0.98 0 0)): Dark text (oklch(0.15 0.02 250)) - Ratio 14.2:1 ✓
  - Accent teal (oklch(0.60 0.18 200)): White text (oklch(0.98 0 0)) - Ratio 4.9:1 ✓
  - Secondary pale grey (oklch(0.92 0.01 250)): Dark text (oklch(0.15 0.02 250)) - Ratio 11.5:1 ✓

## Font Selection

Monospace primary with clean sans-serif for labels and UI chrome to communicate code-aware technical precision while maintaining professional polish.

- **Typographic Hierarchy**: 
  - H1 (Page Title): JetBrains Mono Bold / 32px / letter-spacing: -0.02em / color: accent cyan
  - H2 (Section Headers): JetBrains Mono Medium / 18px / letter-spacing: 0 / color: light gray
  - Body (Editor Content): JetBrains Mono Regular / 14px / line-height: 1.6 / color: light gray
  - Labels (UI Chrome): Inter Medium / 12px / letter-spacing: 0.02em / uppercase / color: muted gray
  - Buttons: Inter Semibold / 14px / letter-spacing: 0 / color: context-dependent

## Animations

Animations should emphasize state transitions in the agent execution flow and provide feedback for technical operations. Use subtle pulsing for loading states, smooth height transitions when toggling result views, and gentle color shifts for authentication status changes. Execution progress should feel systematic with stepped animations rather than continuous spinners.

## Component Selection

- **Components**: 
  - `Tabs` for authentication method selection (Entra vs API Key) and nested tabs for Entra auth type (Managed Identity vs Service Principal)
  - `Card` for main configuration sections (Auth, Prompt, URLs) with adaptive theming
  - `Textarea` for system prompt and URL list with monospace font
  - `Input` for credential fields with appropriate types (password for secrets)
  - `Button` with loading state for agent execution, disabled state during runs
  - `Toggle` for switching between console/markdown result views
  - `ScrollArea` for result display to handle long outputs
  - `Alert` for error messaging and status notifications
  - `Badge` for URL count indicator and execution status
  - `Separator` for visual section division
  - Custom `ThemeToggle` button with sun/moon icons for light/dark mode switching
  
- **Customizations**: 
  - Custom code-editor styling on `Textarea` with monospace font, line numbers appearance, syntax-aware colors
  - Custom authentication status indicator component with icon and color-coded state
  - Custom result viewer with toggle between raw console output and rendered markdown
  
- **States**: 
  - Buttons: Default (electric cyan bg), Hover (brighter cyan), Active (pressed effect), Loading (pulse animation with spinner), Disabled (muted gray)
  - Inputs: Default (dark border), Focus (cyan border glow), Filled (subtle highlight), Error (red border with message)
  - Auth status: Disconnected (gray), Validating (pulsing cyan), Connected (solid green), Failed (red with error icon)
  
- **Icon Selection**: 
  - `Key` for API key authentication
  - `ShieldCheck` for Entra ID authentication  
  - `Cloud` for Managed Identity
  - `UserCircle` for Service Principal
  - `Play` for run agent button
  - `FileCode` for system prompt section
  - `Globe` for URL list section
  - `Terminal` for console view
  - `FileText` for markdown view
  - `Download` for result export
  - `Warning` for error states
  - `CheckCircle` for success states
  - `Sun` for light mode toggle
  - `Moon` for dark mode toggle
  
- **Spacing**: 
  - Section padding: `p-6`
  - Card gaps: `gap-6`
  - Form field gaps: `gap-4`
  - Inline element spacing: `gap-2`
  - Page margins: `p-8`
  
- **Mobile**: 
  - Stack all cards vertically on mobile with full width
  - Reduce padding to `p-4` on cards and `p-4` on page
  - Font sizes scale down: H1 to 24px, H2 to 16px, Body to 13px
  - Hide line number styling in code editors on very small screens
  - Make result viewer default to markdown view on mobile for better readability
  - Sticky execution button at bottom of viewport on mobile for easy access
