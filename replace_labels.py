#!/usr/bin/env python
# Script to replace label rendering method in visualize.py

with open('service/visualize.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the old block
old_block = '''        fig.add_trace(
            go.Scatter(
                x=[x_val],
                y=[placed_y],
                name=text,
                legendgroup=legend_group,
                showlegend=False,
                yaxis="y2",
                mode="text",
                # Jangan keluar area plot supaya tidak "nabrak" komponen lain (mis. tabel)
                cliponaxis=True,
                text=[f"<b>{safe_text}</b>"],
                textposition="middle right",
                textfont=dict(size=LABEL_FONT_SIZE, color=border_color, family="Inter, Arial, sans-serif"),
                hoverinfo="skip",
            )
        )'''

# Define the new block
new_block = '''        # Tambahkan annotation dengan border tipis untuk visual separation
        fig.add_annotation(
            x=x_val,
            y=placed_y,
            text=f"<b>{safe_text}</b>",
            showarrow=False,
            yref="y2",
            xanchor="left",
            yanchor="middle",
            font=dict(size=LABEL_FONT_SIZE, color=border_color, family="Inter, Arial, sans-serif"),
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor=border_color,
            borderwidth=1,
            borderpad=4,
        )'''

# Replace
if old_block in content:
    content = content.replace(old_block, new_block)
    with open('service/visualize.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✓ Replacement successful!')
else:
    print('✗ Old block not found in file')
