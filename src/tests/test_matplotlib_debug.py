#!/usr/bin/env python3
"""
Debug matplotlib LaTeX rendering to see actual errors.
"""

import io
import base64

latex_code = "Var(aX+bY)"

print(f"Testing matplotlib rendering for: {latex_code}")
print("=" * 80)

try:
    import matplotlib.pyplot as plt
    import matplotlib
    print(f"✓ matplotlib imported successfully")
    print(f"  Version: {matplotlib.__version__}")

    matplotlib.use('Agg')
    print(f"✓ Backend set to Agg")

    # Create figure
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.patch.set_alpha(0)
    print(f"✓ Figure created")

    # Render LaTeX
    text = fig.text(
        0, 0,
        f'${latex_code}$',
        fontsize=14,
        color='white',
        usetex=False
    )
    print(f"✓ Text added to figure")

    # Draw
    fig.canvas.draw()
    print(f"✓ Canvas drawn")

    bbox = text.get_window_extent(fig.canvas.get_renderer())
    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())
    bbox_inches = bbox_inches.padded(0.1)
    print(f"✓ Bounding box calculated")

    # Render to PNG
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format='png',
        bbox_inches=bbox_inches,
        transparent=True,
        dpi=150,
        pad_inches=0
    )
    print(f"✓ Saved to buffer")

    plt.close(fig)

    # Encode
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    data_uri = f'data:image/png;base64,{img_base64}'

    print(f"\n✓✓✓ SUCCESS! ✓✓✓")
    print(f"Data URI length: {len(data_uri)} characters")

except Exception as e:
    print(f"\n✗✗✗ ERROR ✗✗✗")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
