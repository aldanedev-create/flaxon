# Jinax Website Example

This example demonstrates a server-rendered website using **Jinax templates** with Flaxon.

Features demonstrated:

- Template inheritance
- Custom filters
- Global template functions
- Dynamic routes
- Server-side rendering
- Static HTML pages


---

# Running the Example

Create a new Flaxon project:

```bash
flaxon new website-example

cd website-example
```

Install dependencies:

```bash
pip install flaxon[standard,templates]
```

Create the application files below.

Run:

```bash
flaxon run app:app --reload
```

Open:

```
http://localhost:8000
```

---

# Application Code

## app.py

```python
from datetime import datetime

from flaxon import Flaxon
from flaxon.jinax import Jinax


app = Flaxon(
    "website",
    debug=True
)


# Configure Jinax templates

app.use_templates(
    Jinax(
        "templates",
        auto_reload=True
    )
)


jinax = app.jinax


# ---------------------
# Custom Filter
# ---------------------

def currency_filter(
    value,
    symbol="$"
):

    try:
        amount = float(value)

        return (
            f"{symbol}{amount:,.2f}"
        )

    except (TypeError, ValueError):

        return value



jinax.add_filter(
    "currency",
    currency_filter
)



# ---------------------
# Global Function
# ---------------------

def current_year():

    return datetime.now().year



jinax.add_global(
    "current_year",
    current_year
)



# ---------------------
# Routes
# ---------------------

@app.get("/")
async def home(request):

    products = [

        {
            "id":1,
            "name":"Flaxon T-Shirt",
            "price":29.99,
            "in_stock":True
        },

        {
            "id":2,
            "name":"Flaxon Mug",
            "price":14.99,
            "in_stock":True
        },

        {
            "id":3,
            "name":"Sticker Pack",
            "price":9.99,
            "in_stock":False
        }

    ]


    return await request.render(
        "home.html",
        {
            "title":"Flaxon Store",
            "products":products
        }
    )



@app.get("/about")
async def about(request):

    return await request.render(
        "about.html",
        {

            "title":
            "About Flaxon",

            "description":
            "Technology-neutral async-first Python full-stack framework.",


            "features":[

                "Async-first architecture",
                "Route decorators",
                "Validation",
                "WebSockets",
                "Middleware",
                "Debugger"

            ]

        }
    )



@app.get("/product/<int:product_id>")
async def product_detail(
    request,
    product_id:int
):

    products = [

        {
            "id":1,
            "name":"Flaxon T-Shirt",
            "price":29.99,
            "description":
            "Premium Flaxon shirt",
            "in_stock":True
        }

    ]


    product = next(
        (
            p for p in products
            if p["id"] == product_id
        ),
        None
    )


    if not product:

        return await request.render(
            "404.html",
            {
                "title":
                "Product Not Found"
            }
        ),404



    return await request.render(
        "product.html",
        {
            "title":
            product["name"],

            "product":
            product
        }
    )



```

Run the example with `flaxon run app:app --reload`.

---

# Template Files

Project structure:

```
website-example/

├── app.py
│
└── templates/
    ├── base.html
    ├── home.html
    ├── about.html
    └── product.html
```

---

# templates/base.html

```html
<!doctype html>

<html>

<head>

<title>
{% block title %}
Flaxon
{% endblock %}
</title>


<style>

body {

font-family:
system-ui;

background:
#f8fafc;

color:
#0f172a;

}


nav {

background:
#0f172a;

padding:
1rem;

}


nav a {

color:white;

margin-right:1rem;

}


.card {

background:white;

padding:20px;

border-radius:10px;

margin:10px;

}


.price {

color:#0284c7;

font-weight:bold;

}

</style>


</head>


<body>


<nav>

<strong>
Flaxon
</strong>

<a href="/">
Home
</a>


<a href="/about">
About
</a>


</nav>



<main>

{% block content %}

{% endblock %}

</main>



<footer>

<p>

© {{ current_year() }}
Flaxon

</p>

</footer>


</body>

</html>
```

---

# templates/home.html

```html
{% extends "base.html" %}


{% block title %}

{{title}}

{% endblock %}



{% block content %}

<h1>
Welcome to Flaxon Store
</h1>


<div>

{% for product in products %}


<div class="card">


<h3>

{{product.name}}

</h3>


<p class="price">

{{product.price|currency("USD")}}

</p>



<a href="/product/{{product.id}}">

View Product

</a>


</div>


{% endfor %}

</div>


{% endblock %}
```

---

# templates/about.html

```html
{% extends "base.html" %}


{% block content %}


<h1>

{{title}}

</h1>


<p>

{{description}}

</p>



<h2>
Features
</h2>


<ul>

{% for feature in features %}

<li>

{{feature}}

</li>

{% endfor %}

</ul>


{% endblock %}
```

---

# templates/product.html

```html
{% extends "base.html" %}


{% block content %}


<h1>

{{product.name}}

</h1>


<p class="price">

{{product.price|currency("USD")}}

</p>


<p>

{{product.description}}

</p>



{% if product.in_stock %}

<p>
✓ Available
</p>

{% else %}

<p>
Out of stock
</p>

{% endif %}



<button>

Add To Cart

</button>


{% endblock %}
```

---

# Development

Run:

```bash
pip install flaxon[standard,templates]

flaxon run app:app --reload
```

Visit:

```
http://localhost:8000
```

You should see the Jinax server-rendered website.

---

# Features Demonstrated

✅ Template inheritance  
✅ Custom template filters  
✅ Global functions  
✅ Dynamic routes  
✅ HTML rendering  
✅ Server-side applications with Flaxon + Jinax
