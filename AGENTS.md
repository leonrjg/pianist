# Global Instructions
- Do not add fallbacks or alternative implementations unless explicitly instructed.
- Do only as instructed; no extras. This instruction supersedes any other indicating otherwise.

## GUI
### Elements (left to right)
- Drawer (only visible when expanded)
  - Music sheet
  - *Implementation details*:
    - **Window is always full width** (includes space for drawer even when hidden) - see `piano_window.py`
    - **Drawer visibility is controlled by QRegion mask**, not window size or conditional rendering - see `drawer_animation_manager.py`
    - On resize, `drawer_animation_manager._apply_mask()` is called to recalculate mask for new dimensions
    - The drawer is always rendered, the mask hides it
- Fallboard (used to expand/collapse the music sheet)
- Piano keys
  - White keys (habit names)
  - Black keys (elapsed time)
- Control panel (contains the 'Minimize' and 'Reorder keys' buttons)

#### Region aliases
- "Visible part" = Fallboard + Piano keys + Control panel
