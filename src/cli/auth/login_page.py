"""
HTML page served after a successful OIDC login callback.

The logo SVG is loaded from logo.svg at import time and embedded inline
in the page to avoid external requests.
"""

from importlib.resources import files


def _load_logo_svg() -> str:
    """
    Load the Hiverge logo SVG from the package data.
    """
    return files(__package__).joinpath("logo.svg").read_text(encoding="utf-8")


_LOGO_SVG = _load_logo_svg()

LOGIN_SUCCESS_HTML: bytes = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login Successful</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Funnel+Display:wght@400;500;600&family=Outfit:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; }}
  body {{
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: 'Outfit', sans-serif;
    background: #fafafa;
    color: #111;
  }}
  .container {{
    text-align: center;
  }}
  .logo {{
    margin-bottom: 24px;
  }}
  .logo svg {{
    width: 280px;
    height: auto;
  }}
  h1 {{
    font-family: 'Funnel Display', sans-serif;
    font-weight: 500;
    font-size: 28px;
    margin-bottom: 12px;
  }}
  p {{
    font-weight: 300;
    font-size: 16px;
    color: #555;
  }}
  p a {{
    color: #555;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="logo">
    {_LOGO_SVG}
  </div>
  <h1>Login successful!</h1>
  <p>You can <a href="javascript:window.close()">close this window</a> and return to the Hive CLI.</p>
</div>
</body>
</html>""".encode()
