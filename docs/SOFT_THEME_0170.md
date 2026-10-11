# Soft midnight visual update

October 11, 2026. Presentation-only update to Financial Friday 0.17.0.

The former jade palette is replaced with midnight lavender, lilac actions and
peach accents. Rounded overview surfaces, four colour-coded task cards, lighter
headline weight and a combined input/action surface make the interface gentler.
The HUD aperture remains animated and now uses lavender in its ready state.

Success remains mint, held results remain rose and review remains amber, alongside
written labels. Focus outlines, mobile stacking and reduced-motion controls are
retained. Decorative task arrows do not change accessible button names. Hover
movement applies only to enabled buttons and respects motion-off preferences.

No financial decisions, model tools, permissions, inputs or execution routes were
changed. No new tracking or dependency was introduced. The palette is loaded last
after the existing layouts; it does not hide financial controls or disclaimers.

Native validation: 302 tests, 301 passed and one optional skip. A regression check
covers stylesheet order, outcome states, focus/reduced-motion selectors and the
absence of script or hidden-control rules. Screenshots and browser checks are
targeted validation, not an accessibility certification.

## Release evidence

Source: `c8d3a5c`. Cloud Build `69f87374-fa0b-4880-b344-4139e147b1b4`
completed successfully. Web revision `soft1011` serves 100% of live traffic using
image digest `sha256:04ea4f200c12b22d6bdba0b5896820003caaf4ce4182878acf70b2faecb309f3`.
The API remains on `core1011b`; IAP and private backend protections are unchanged.
Docker validation: 302 tests, 290 passed and twelve optional skips. Fresh browser
checks covered Home, document intake and read-only successful receipt reopening;
no console errors or warnings were returned. The transition's initial fade frame
was distinguished from the fully visible document screen. No payment was rerun.
Screenshots are in the workspace's `audit-friday-core` folder.
