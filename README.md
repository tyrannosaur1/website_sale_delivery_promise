# Delivery Promise for the Website

Show shoppers when the order will actually arrive, computed from the shop's own calendar instead of a fixed text.

Odoo 16.0 – 20.0. One branch per series, the branch name is the series.

## What it does

- "Order within 3h 12m, delivered by Fri, 30 Oct" on the product page, in the cart and at checkout.
- A daily cut-off per website: an order placed after it is prepared the next working day.
- A working week per website, holidays per website, and extra transit days per destination country, all walked over closed days.
- Preparation time per product, either a number of working days or "follow the Sales Lead Time".
- The cart promises the date of its slowest line, not the sum of the lines.
- At confirmation the promise is written on the order as its commitment date, and a date the merchant typed is never overwritten.

## Install

1. Copy the module into your addons path.
2. Update the app list, install **Delivery Promise for the Website**.
3. Website › Configuration › Settings: set the cut-off, the working days, the holidays and the transit days per country.

## Translations

Chinese, Spanish, German, French, Italian, Dutch, Polish, Brazilian Portuguese and Russian ship with the module.

## License

OPL-1. See `LICENSE`.

## Support

Open an issue on this repository.
