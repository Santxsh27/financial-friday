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
