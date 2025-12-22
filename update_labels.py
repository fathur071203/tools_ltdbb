#!/usr/bin/env python3
"""Script to add border styling to chart labels."""

with open('service/visualize.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the fig.add_trace block with annotation version
old_trace = '''        fig.add_trace(
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

new_annotation = '''        # Tambahkan annotation dengan border tipis untuk visual separation
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

new_content = content.replace(old_trace, new_annotation)

with open('service/visualize.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('✓ Replaced add_trace with add_annotation for label borders')
