# Product HTML Generator

A simple web-based tool to generate HTML blocks for products from an Excel file.

## Features
- Upload an Excel file with product data (title, price, description, image_url).
- Download a single HTML file with all product blocks filled in.

## How to Run

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Start the server:
   ```
   python app.py
   ```
3. Open your browser and go to [http://localhost:5000](http://localhost:5000)
4. Upload your Excel file (see `sample_products.xlsx` for format).
5. Download the generated HTML file.

## Sample Excel Format

| title        | price | description      | image_url                |
|--------------|-------|------------------|--------------------------|
| Product 1    | 10    | First product    | https://via.placeholder.com/200 |
| Product 2    | 20    | Second product   | https://via.placeholder.com/200 |

## Customization
- Edit `templates/sample_template.html` to change the HTML block format.
- The placeholders (e.g., `{{title}}`) must match the column names in your Excel file.

---

**Deployable and ready to use!**
