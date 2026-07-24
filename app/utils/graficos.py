"""Gráficos de barras en SVG (server-side, sin dependencias ni CDN).

Se renderizan inline en la página, escalan al 100% del contenedor y usan la
paleta de marca. Pensado para funcionar offline en cualquier PC.
"""

MESES_ABREV = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def fmt_entero(v):
    return f"{int(round(v))}"


def fmt_compacto(v):
    """Formato compacto para etiquetas: 7.538.000 -> '7,5M' ; 5400 -> '5,4k'."""
    v = float(v or 0)
    if v >= 1_000_000:
        return f"{v/1e6:.1f}".replace(".", ",").rstrip("0").rstrip(",") + "M"
    if v >= 1_000:
        txt = f"{v/1e3:.1f}".replace(".", ",") if v < 10_000 else f"{v/1e3:.0f}"
        return txt + "k"
    return f"{v:.0f}"


def grafico_barras(labels, series, colores, apilado=False, formato=fmt_entero,
                   alto=240, ancho=720, mostrar_valores=True):
    """Devuelve un string SVG con un gráfico de barras.

    labels  : lista de etiquetas (eje X).
    series  : lista de series; cada serie es una lista de números (len == labels).
    colores : lista de colores hex, uno por serie.
    apilado : si True apila las series; si False las agrupa lado a lado.
    """
    n = len(labels)
    ml, mr, mt, mb = 12, 12, 26, 30
    pw = ancho - ml - mr
    ph = alto - mt - mb
    base_y = alto - mb

    if not series or n == 0:
        maxv = 1
    elif apilado:
        maxv = max((sum(s[i] for s in series) for i in range(n)), default=0)
    else:
        maxv = max((max(s) for s in series if s), default=0)
    maxv = maxv or 1

    gw = pw / n if n else pw
    p = []
    p.append(f'<line x1="{ml}" y1="{base_y:.1f}" x2="{ancho-mr}" y2="{base_y:.1f}" '
             f'stroke="#e3e8ef" stroke-width="1"/>')

    for i, lab in enumerate(labels):
        gx = ml + i * gw
        if apilado:
            bw = min(gw * 0.52, 46)
            bx = gx + (gw - bw) / 2
            ycur = base_y
            total = sum(s[i] for s in series)
            for si, s in enumerate(series):
                val = s[i]
                if val <= 0:
                    continue
                h = val / maxv * ph
                y = ycur - h
                p.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                         f'rx="3" fill="{colores[si]}"/>')
                ycur = y
            if mostrar_valores and total > 0:
                p.append(f'<text x="{bx+bw/2:.1f}" y="{ycur-6:.1f}" text-anchor="middle" '
                         f'font-size="11" font-weight="600" fill="#6E6E73">{formato(total)}</text>')
        else:
            ns = len(series)
            gap = 4
            bw = min((gw * 0.6 - gap * (ns - 1)) / ns, 48)
            tot_w = bw * ns + gap * (ns - 1)
            start = gx + (gw - tot_w) / 2
            for si, s in enumerate(series):
                val = s[i]
                h = max(val / maxv * ph, 0)
                x = start + si * (bw + gap)
                y = base_y - h
                if val > 0:
                    p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                             f'rx="3" fill="{colores[si]}"/>')
                    if mostrar_valores:
                        p.append(f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" text-anchor="middle" '
                                 f'font-size="10" font-weight="600" fill="#6E6E73">{formato(val)}</text>')
        p.append(f'<text x="{gx+gw/2:.1f}" y="{base_y+18:.1f}" text-anchor="middle" '
                 f'font-size="11" fill="#86868B">{lab}</text>')

    return (f'<svg viewBox="0 0 {ancho} {alto}" xmlns="http://www.w3.org/2000/svg" '
            f'style="width:100%;height:auto;display:block;font-family:inherit">'
            + "".join(p) + "</svg>")
