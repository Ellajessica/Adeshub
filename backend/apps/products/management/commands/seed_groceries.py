from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.products.models import Category, Product, ProductVariant


class Command(BaseCommand):
    help = 'Safely seeds/expands the 15 required AdesHub African grocery categories with at least 3 distinct products each (45 total products).'

    def handle(self, *args, **options):
        self.stdout.write('Expanding AdesHub grocery categories and catalogue...')

        # 1. DEFINE AND SYNC THE 15 CATEGORIES
        categories_def = [
            {
                'name': 'Rice & Grains',
                'slug': 'rice-grains',
                'description': 'Authentic African parboiled rice, aged fragrant ofada, and nutritious staple grains.'
            },
            {
                'name': 'Garri & Cassava Products',
                'slug': 'garri-cassava-products',
                'description': 'Crispy Ijebu garri, yellow cassava garri enriched with palm oil, and smooth white fufu.'
            },
            {
                'name': 'Beans & Legumes',
                'slug': 'beans-legumes',
                'description': 'Naturally sweet honey brown beans (Oloyin), peeled black-eyed beans, and versatile legumes.'
            },
            {
                'name': 'Flour & Baking Ingredients',
                'slug': 'flour-baking-ingredients',
                'description': 'Traditional pounded yam flour (Iyan), plantain flour, and brown amala yam flour.'
            },
            {
                'name': 'Palm Oil & Cooking Oils',
                'slug': 'palm-oil-cooking-oils',
                'description': '100% unadulterated red palm oil, spiced zomi oil, and pure golden groundnut oil.'
            },
            {
                'name': 'Spices & Seasonings',
                'slug': 'spices-seasonings',
                'description': 'Spicy suya pepper (Yaji), Cameroon pepper, ground African nutmeg (Ehuru), and seasonings.'
            },
            {
                'name': 'Soups & Stew Ingredients',
                'slug': 'soups-stew-ingredients',
                'description': 'Whole shelled melon seeds (Egusi), wild mango seeds (Ogbono), and sun-dried bitter leaves.'
            },
            {
                'name': 'Dried Fish & Seafood',
                'slug': 'dried-fish-seafood',
                'description': 'Hardwood smoked catfish, whole Norwegian stockfish fillets, and aromatic crayfish powder.'
            },
            {
                'name': 'Meat & Frozen Foods',
                'slug': 'meat-frozen-foods',
                'description': 'Tender smoked goat meat pieces, soft cow skin (Ponmo / Kanda), and seasoned boiling fowl.'
            },
            {
                'name': 'Snacks & Biscuits',
                'slug': 'snacks-biscuits',
                'description': 'Crispy plantain chips, crunchy sweet chin chin, and classic Nigerian teatime biscuits.'
            },
            {
                'name': 'Drinks & Beverages',
                'slug': 'drinks-beverages',
                'description': 'Chilled Malta Guinness cans, Supermalt classic, and organic dried hibiscus flowers (Zobo).'
            },
            {
                'name': 'Noodles & Pasta',
                'slug': 'noodles-pasta',
                'description': 'Indomie Hungryman instant noodles, Jollof flavour noodles, and African durum macaroni.'
            },
            {
                'name': 'Yam & Plantain',
                'slug': 'yam-plantain',
                'description': 'Fresh Ghanaian white Pona yams, crisp green cooking plantains, and sweet yellow plantains.'
            },
            {
                'name': 'African Breakfast Foods',
                'slug': 'african-breakfast-foods',
                'description': 'Traditional fermented corn puree (Ogi / Akamu), smooth vanilla custard, and Milo food drink.'
            },
            {
                'name': 'Traditional Food Ingredients',
                'slug': 'traditional-food-ingredients',
                'description': 'Fermented locust beans (Iru / Dawadawa), Ogiri Igbo soup seasoning, and natural cooking potash.'
            },
        ]

        # Re-use existing categories if applicable to prevent duplicates
        category_map = {}

        # Check existing Category 6 and 7
        try:
            cat6 = Category.objects.filter(id=6).first()
            if cat6:
                cat6.name = 'Rice & Grains'
                cat6.slug = 'rice-grains'
                cat6.description = categories_def[0]['description']
                cat6.is_active = True
                cat6.save()
                category_map['rice-grains'] = cat6
        except Exception:
            pass

        try:
            cat7 = Category.objects.filter(id=7).first()
            if cat7:
                cat7.name = 'Palm Oil & Cooking Oils'
                cat7.slug = 'palm-oil-cooking-oils'
                cat7.description = categories_def[4]['description']
                cat7.is_active = True
                cat7.save()
                category_map['palm-oil-cooking-oils'] = cat7
        except Exception:
            pass

        for cdata in categories_def:
            slug = cdata['slug']
            if slug in category_map:
                continue
            cat = Category.objects.filter(slug=slug).first()
            if not cat:
                cat = Category.objects.filter(name=cdata['name']).first()
            if cat:
                cat.name = cdata['name']
                cat.slug = slug
                cat.description = cdata['description']
                cat.is_active = True
                cat.save()
            else:
                cat = Category.objects.create(
                    name=cdata['name'],
                    slug=slug,
                    description=cdata['description'],
                    is_active=True
                )
            category_map[slug] = cat

        self.stdout.write(f'Synchronized {len(category_map)} categories.')

        # 2. SEED AT LEAST 3 DISTINCT PRODUCTS PER CATEGORY (45 TOTAL)
        # Note: Preserves Product ID 8 ('BEANS-001') and Product ID 9 ('PALM-001')
        products_def = [
            # 1. Rice & Grains
            {
                'sku': 'DEV-RICE-01',
                'name': 'Mama Gold African Parboiled Rice 5kg',
                'category_slug': 'rice-grains',
                'price': Decimal('14.50'),
                'compare_at_price': Decimal('16.00'),
                'stock_quantity': 18,
                'description': 'Premium quality long-grain parboiled rice specially milled for firm grains that cook up fluffy and non-sticky. Perfect for Nigerian party Jollof rice, fried rice, and hearty everyday stew dinners.',
                'is_featured': True
            },
            {
                'sku': 'DEV-RICE-02',
                'name': 'Royal Stallion Long Grain Parboiled Rice 10kg',
                'category_slug': 'rice-grains',
                'price': Decimal('24.99'),
                'compare_at_price': Decimal('27.50'),
                'stock_quantity': 12,
                'description': 'Bulk family sack of authentic long-grain parboiled rice with rich texture and clean grains. Ideal for large family gatherings, Sunday roasts, and weekend catering.',
                'is_featured': False
            },
            {
                'sku': 'DEV-RICE-03',
                'name': 'Akani Ofada Unpolished Local Rice 2kg',
                'category_slug': 'rice-grains',
                'price': Decimal('9.20'),
                'compare_at_price': None,
                'stock_quantity': 14,
                'description': 'Aromatic, nutrient-rich unpolished indigenous short-grain rice with signature earthy fragrance. The essential companion to spicy Ayamase (designer stew) and fried plantains.',
                'is_featured': False
            },

            # 2. Garri & Cassava Products
            {
                'sku': 'DEV-GARRI-01',
                'name': 'Ijebu Garri Premium Crispy 4kg',
                'category_slug': 'garri-cassava-products',
                'price': Decimal('8.50'),
                'compare_at_price': Decimal('9.50'),
                'stock_quantity': 25,
                'description': 'Crispy, pleasantly sour, fine-grained Ijebu white garri processed from freshly harvested cassava roots. Marvelous for ice-cold garri drinking with groundnuts and milk, or prepared into firm smooth Eba.',
                'is_featured': True
            },
            {
                'sku': 'DEV-GARRI-02',
                'name': 'Yellow Cassava Garri (Enriched with Palm Oil) 5kg',
                'category_slug': 'garri-cassava-products',
                'price': Decimal('9.99'),
                'compare_at_price': None,
                'stock_quantity': 15,
                'description': 'Traditional delta yellow garri fortified with fresh red palm oil during roasting. Produces smooth, golden Eba that pairs beautifully with Ofe Nsala, Ogbono, and Banga soup.',
                'is_featured': False
            },
            {
                'sku': 'DEV-GARRI-03',
                'name': 'Processed White Fufu Flour 2kg',
                'category_slug': 'garri-cassava-products',
                'price': Decimal('5.50'),
                'compare_at_price': None,
                'stock_quantity': 16,
                'description': 'Convenient, odor-free fermented cassava fufu flour. Simply stir into boiling water for a velvety, stretchy swallow ready in minutes to accompany egusi and vegetable soups.',
                'is_featured': False
            },

            # 3. Beans & Legumes (Product 8 BEANS-001 is mapped here)
            {
                'sku': 'BEANS-001',
                'name': 'Brown Beans 5kg (Honey Oloyin)',
                'category_slug': 'beans-legumes',
                'price': Decimal('12.50'),
                'compare_at_price': Decimal('14.00'),
                'stock_quantity': 7,
                'description': 'Premium quality African honey brown beans (Oloyin). Naturally sweet, nutrient-dense, and fast-cooking. Perfect for preparing traditional Nigerian dishes such as Gbegiri soup, Ewa Aganyin, steamed Moin Moin, and Akara bean cakes.',
                'is_featured': True
            },
            {
                'sku': 'DEV-BEANS-02',
                'name': 'Peeled Black-Eyed Beans for Moin Moin 2kg',
                'category_slug': 'beans-legumes',
                'price': Decimal('6.80'),
                'compare_at_price': None,
                'stock_quantity': 20,
                'description': 'Ready-to-blend skinless white black-eyed beans. Eliminates the time-consuming soaking and washing step so you can prepare smooth, fluffy Moin Moin and golden Akara with ease.',
                'is_featured': False
            },
            {
                'sku': 'DEV-BEANS-03',
                'name': 'Nigerian White Soya Beans 1.5kg',
                'category_slug': 'beans-legumes',
                'price': Decimal('4.95'),
                'compare_at_price': None,
                'stock_quantity': 12,
                'description': 'High-protein, clean whole soya beans. Widely used for making nutritious homemade soymilk, baby weaning porridge, and savory soya bean patties (Awara / Tofu).',
                'is_featured': False
            },

            # 4. Flour & Baking Ingredients
            {
                'sku': 'DEV-FLOUR-01',
                'name': 'Ola-Ola Authentic Pounded Yam Flour (Iyan) 1.8kg',
                'category_slug': 'flour-baking-ingredients',
                'price': Decimal('11.50'),
                'compare_at_price': Decimal('12.99'),
                'stock_quantity': 22,
                'description': 'The UK’s favorite pounded yam flour. Delivers exceptionally smooth, elastic, lump-free pounded yam in just 5 minutes without the labor of a mortar and pestle.',
                'is_featured': True
            },
            {
                'sku': 'DEV-FLOUR-02',
                'name': 'Golden Tropics Plantain Flour (Elubo Ogede) 2kg',
                'category_slug': 'flour-baking-ingredients',
                'price': Decimal('7.95'),
                'compare_at_price': None,
                'stock_quantity': 16,
                'description': '100% natural green unripe plantain flour. Low glycemic index swallow rich in dietary fiber, potassium, and essential vitamins for clean, wholesome African dinners.',
                'is_featured': False
            },
            {
                'sku': 'DEV-FLOUR-03',
                'name': 'Traditional Brown Yam Flour (Elubo Amala) 2kg',
                'category_slug': 'flour-baking-ingredients',
                'price': Decimal('8.25'),
                'compare_at_price': None,
                'stock_quantity': 18,
                'description': 'Authentic sun-dried yam peel flour yielding deep brown, fluffy Amala Dudu. The quintessential match for steaming hot Ewedu, Gbegiri, and spicy pepper stew with goat meat.',
                'is_featured': False
            },

            # 5. Palm Oil & Cooking Oils (Product 9 PALM-001 is mapped here)
            {
                'sku': 'PALM-001',
                'name': 'Palm Oil (Pure Red African Palm Oil)',
                'category_slug': 'palm-oil-cooking-oils',
                'price': Decimal('5.00'),
                'compare_at_price': None,
                'stock_quantity': 10,
                'description': '100% pure, unadulterated red palm oil with rich authentic aroma and deep crimson hue. Free from additives and artificial coloring. An essential cooking base for authentic African soups including Egusi, Ogbono, Banga, and native stews.',
                'is_featured': True
            },
            {
                'sku': 'DEV-OIL-02',
                'name': 'Zomi Spiced Red Palm Oil 1 Litre',
                'category_slug': 'palm-oil-cooking-oils',
                'price': Decimal('6.50'),
                'compare_at_price': None,
                'stock_quantity': 14,
                'description': 'Gently infused traditional palm oil seasoned with African aromatics. Imparts a rich smoked flavor and golden finish to beans porridge, roasted yam, and native stews.',
                'is_featured': False
            },
            {
                'sku': 'DEV-OIL-03',
                'name': 'Pure Groundnut Oil (Pure Peanut Oil) 2 Litres',
                'category_slug': 'palm-oil-cooking-oils',
                'price': Decimal('7.80'),
                'compare_at_price': None,
                'stock_quantity': 16,
                'description': 'Triple-filtered golden peanut oil with high smoke point and neutral finish. Ideal for crisp frying of dodo (ripe plantain), puff puff, yam chips, and beef stew.',
                'is_featured': False
            },

            # 6. Spices & Seasonings
            {
                'sku': 'DEV-SPICE-01',
                'name': 'Authentic Nigerian Suya Pepper Spice (Yaji) 200g',
                'category_slug': 'spices-seasonings',
                'price': Decimal('3.99'),
                'compare_at_price': Decimal('4.50'),
                'stock_quantity': 30,
                'description': 'Classic Northern Nigerian barbecue dry rub blend featuring roasted groundnut flour, crushed ginger, chili, garlic, and sea salt. Unbeatable on grilled beef, chicken, and roasted corn.',
                'is_featured': True
            },
            {
                'sku': 'DEV-SPICE-02',
                'name': 'Whole Cameroon Pepper Powder Hot 150g',
                'category_slug': 'spices-seasonings',
                'price': Decimal('3.50'),
                'compare_at_price': None,
                'stock_quantity': 25,
                'description': 'Dark smoked, deeply fragrant fiery chili pepper from the Cameroon coastal hills. Gives West African stews, pepper soups, and braised meats an unmistakable smoky warmth.',
                'is_featured': False
            },
            {
                'sku': 'DEV-SPICE-03',
                'name': 'Ground African Nutmeg (Ehuru) 100g',
                'category_slug': 'spices-seasonings',
                'price': Decimal('2.99'),
                'compare_at_price': None,
                'stock_quantity': 22,
                'description': 'Wild calabar nutmeg roasted and freshly ground. Imparts the hallmark aromatic, warming scent in genuine Nigerian goat meat pepper soup, Banga soup, and Isi Ewu.',
                'is_featured': False
            },

            # 7. Soups & Stew Ingredients
            {
                'sku': 'DEV-SOUP-01',
                'name': 'Whole Shelled Melon Seeds (Egusi) 1kg',
                'category_slug': 'soups-stew-ingredients',
                'price': Decimal('8.99'),
                'compare_at_price': Decimal('9.99'),
                'stock_quantity': 20,
                'description': 'Hand-selected, thoroughly dried organic African melon seeds. Blend into rich nutty paste to cook Nigeria’s most famous celebratory soup with assorted meats and bitter leaf.',
                'is_featured': True
            },
            {
                'sku': 'DEV-SOUP-02',
                'name': 'Ground Wild Mango Seeds (Ogbono / Apon) 500g',
                'category_slug': 'soups-stew-ingredients',
                'price': Decimal('9.50'),
                'compare_at_price': None,
                'stock_quantity': 18,
                'description': 'Pure indigenous dika nut powder with incredible viscosity and draw. Melts smoothly into hot palm oil base to create rich, comforting Ogbono soup.',
                'is_featured': False
            },
            {
                'sku': 'DEV-SOUP-03',
                'name': 'Pounded Bitter Leaf Dried (Ogbu) 250g',
                'category_slug': 'soups-stew-ingredients',
                'price': Decimal('4.20'),
                'compare_at_price': None,
                'stock_quantity': 24,
                'description': 'Carefully washed and oven-dried vernonia leaves. Retains pleasant herbaceous bitterness and medicinal qualities for Ofe Onugbu and assorted meat pepper soups.',
                'is_featured': False
            },

            # 8. Dried Fish & Seafood
            {
                'sku': 'DEV-FISH-01',
                'name': 'Smoked Dried Mangrove Catfish 400g',
                'category_slug': 'dried-fish-seafood',
                'price': Decimal('11.99'),
                'compare_at_price': Decimal('13.50'),
                'stock_quantity': 14,
                'description': 'Naturally smoked whole African river catfish with deep mahogany skin and firm, savory flesh. Rehydrates gently in simmering soups to release rich smoky umami.',
                'is_featured': True
            },
            {
                'sku': 'DEV-FISH-02',
                'name': 'Whole Dried Stockfish Fillets (Cod) 500g',
                'category_slug': 'dried-fish-seafood',
                'price': Decimal('15.50'),
                'compare_at_price': None,
                'stock_quantity': 10,
                'description': 'Arctic wind-cured cod fish fillets (Okporoko) imported from Lofoten, Norway. Essential for authentic Igbo and Yoruba celebratory soups and wedding feasts.',
                'is_featured': False
            },
            {
                'sku': 'DEV-FISH-03',
                'name': 'Smoked Ground Crayfish Powder 250g',
                'category_slug': 'dried-fish-seafood',
                'price': Decimal('5.75'),
                'compare_at_price': None,
                'stock_quantity': 28,
                'description': '100% pure sun-dried Oron saltwater crayfish freshly ground without sand, fillers, or additives. The foundational secret seasoning of West African culinary tradition.',
                'is_featured': False
            },

            # 9. Meat & Frozen Foods
            {
                'sku': 'DEV-MEAT-01',
                'name': 'Pre-cut Smoked Goat Meat Pieces 1kg',
                'category_slug': 'meat-frozen-foods',
                'price': Decimal('13.99'),
                'compare_at_price': Decimal('15.00'),
                'stock_quantity': 15,
                'description': 'Tender, hardwood-smoked goat meat cut into neat stewing chunks. Ideal for slow simmered goat meat pepper soup, asun, and rich tomato party stews.',
                'is_featured': True
            },
            {
                'sku': 'DEV-MEAT-02',
                'name': 'Premium Smoked Cow Skin (Ponmo / Kanda) 800g',
                'category_slug': 'meat-frozen-foods',
                'price': Decimal('8.50'),
                'compare_at_price': None,
                'stock_quantity': 18,
                'description': 'Thoroughly scraped, boiled, and gently smoked thick beef skin. Tender with satisfying gelatinous bite that absorbs all the savory spices in your soup pot.',
                'is_featured': False
            },
            {
                'sku': 'DEV-MEAT-03',
                'name': 'Seasoned Hard Chicken Boiling Fowl Cut 1.2kg',
                'category_slug': 'meat-frozen-foods',
                'price': Decimal('7.99'),
                'compare_at_price': None,
                'stock_quantity': 16,
                'description': 'Traditional free-range laying fowl with firm, flavor-packed meat. Holds its shape through extended simmering to yield incredibly rich, golden chicken broth.',
                'is_featured': False
            },

            # 10. Snacks & Biscuits
            {
                'sku': 'DEV-SNACK-01',
                'name': 'Crispy Spicy Plantain Chips Pack (10 x 50g)',
                'category_slug': 'snacks-biscuits',
                'price': Decimal('7.50'),
                'compare_at_price': Decimal('8.50'),
                'stock_quantity': 25,
                'description': 'Golden, wafer-thin crunchy slices of green plantains seasoned with fine sea salt and mild habanero pepper. The perfect on-the-go African snack for school or work.',
                'is_featured': True
            },
            {
                'sku': 'DEV-SNACK-02',
                'name': 'Traditional African Chin Chin Crunchy 500g',
                'category_slug': 'snacks-biscuits',
                'price': Decimal('4.99'),
                'compare_at_price': None,
                'stock_quantity': 30,
                'description': 'Sweet, crispy, bite-sized fried pastry enriched with creamy milk, sugar, and warm nutmeg. Baked to golden perfection for afternoon tea and celebratory tables.',
                'is_featured': False
            },
            {
                'sku': 'DEV-SNACK-03',
                'name': 'Cabin Biscuits Classic Tin 900g',
                'category_slug': 'snacks-biscuits',
                'price': Decimal('6.20'),
                'compare_at_price': None,
                'stock_quantity': 20,
                'description': 'Nostalgic crisp square teatime biscuits lightly sweet and delightfully crunchy. A beloved African childhood classic best enjoyed dipped in sweet warm milk or tea.',
                'is_featured': False
            },

            # 11. Drinks & Beverages
            {
                'sku': 'DEV-DRINK-01',
                'name': 'Malta Guinness Non-Alcoholic Malt Drink (6 x 330ml)',
                'category_slug': 'drinks-beverages',
                'price': Decimal('7.20'),
                'compare_at_price': Decimal('8.00'),
                'stock_quantity': 25,
                'description': 'Africa’s number one nourishing malt drink loaded with B-vitamins, minerals, and rich caramelized barley sweetness. Serve ice-cold on hot sunny afternoons.',
                'is_featured': True
            },
            {
                'sku': 'DEV-DRINK-02',
                'name': 'Supermalt Classic Enriched Malt Can (6 x 330ml)',
                'category_slug': 'drinks-beverages',
                'price': Decimal('6.99'),
                'compare_at_price': None,
                'stock_quantity': 22,
                'description': 'Smooth, velvety non-alcoholic malt beverage crafted with natural ingredients and fortified with essential vitamins. A refreshing staple in Afro-Caribbean gatherings.',
                'is_featured': False
            },
            {
                'sku': 'DEV-DRINK-03',
                'name': 'Dried Hibiscus Sorrel Flowers (Zobo / Bissap) 300g',
                'category_slug': 'drinks-beverages',
                'price': Decimal('3.80'),
                'compare_at_price': None,
                'stock_quantity': 35,
                'description': 'Whole dried crimson calyces of Hibiscus sabdariffa. Boil with crushed pineapple peel, ginger, and cloves for a refreshing, antioxidant-rich iced Zobo tea.',
                'is_featured': False
            },

            # 12. Noodles & Pasta
            {
                'sku': 'DEV-NOOD-01',
                'name': 'Indomie Instant Noodles Hungryman Onion Chicken (40 x 180g Carton)',
                'category_slug': 'noodles-pasta',
                'price': Decimal('23.50'),
                'compare_at_price': Decimal('26.00'),
                'stock_quantity': 15,
                'description': 'The legendary jumbo portion of Nigerian Indomie noodles flavored with rich onion chicken seasoning oil and chili flakes. Quick, filling, and extraordinarily delicious.',
                'is_featured': True
            },
            {
                'sku': 'DEV-NOOD-02',
                'name': 'Indomie Jollof Flavour Instant Noodles (40 x 70g)',
                'category_slug': 'noodles-pasta',
                'price': Decimal('16.99'),
                'compare_at_price': None,
                'stock_quantity': 18,
                'description': 'Full carton of zesty jollof pepper seasoned noodles. Infused with tomatoes, bell peppers, and savory herbs for that distinctive party jollof aroma in 3 minutes.',
                'is_featured': False
            },
            {
                'sku': 'DEV-NOOD-03',
                'name': 'Golden Penny African Macaroni Pasta 500g',
                'category_slug': 'noodles-pasta',
                'price': Decimal('1.80'),
                'compare_at_price': None,
                'stock_quantity': 40,
                'description': 'High-protein durum wheat elbow macaroni specially formulated to stay firm in stir-fries. Popular for preparing vibrant spicy Jollof macaroni with bell peppers and sausage.',
                'is_featured': False
            },

            # 13. Yam & Plantain
            {
                'sku': 'DEV-TUBER-01',
                'name': 'Fresh Ghanaian White Pona Yam Tubers (Pack of 2 approx 4kg)',
                'category_slug': 'yam-plantain',
                'price': Decimal('12.99'),
                'compare_at_price': Decimal('14.50'),
                'stock_quantity': 18,
                'description': 'Grade-A imported Ghanaian Pona yams with clean dry skin and sweet, floury white flesh. Boils up tender for garden egg sauce, or fries into crisp Dundun.',
                'is_featured': True
            },
            {
                'sku': 'DEV-TUBER-02',
                'name': 'Fresh Green Unripe Plantains (Box of 8 pcs)',
                'category_slug': 'yam-plantain',
                'price': Decimal('7.95'),
                'compare_at_price': None,
                'stock_quantity': 20,
                'description': 'Crisp, firm green unripe plantains harvested fresh. Perfect for diabetic-friendly boiled plantain with vegetable stew, or roasted over hot charcoal (Boli).',
                'is_featured': False
            },
            {
                'sku': 'DEV-TUBER-03',
                'name': 'Fresh Semi-Ripe Yellow Plantains (Box of 8 pcs)',
                'category_slug': 'yam-plantain',
                'price': Decimal('8.25'),
                'compare_at_price': None,
                'stock_quantity': 22,
                'description': 'Naturally ripened sweet yellow plantains. Slice and deep fry into irresistible golden Dodo, or bake into savory plantain frittata and Gizdodo.',
                'is_featured': False
            },

            # 14. African Breakfast Foods
            {
                'sku': 'DEV-BKFST-01',
                'name': 'Brown Ogi / Akamu Fermented Corn Puree 1kg',
                'category_slug': 'african-breakfast-foods',
                'price': Decimal('4.50'),
                'compare_at_price': None,
                'stock_quantity': 18,
                'description': 'Smooth traditionally fermented yellow and brown guinea corn custard paste. Whisk into boiling water for creamy, tangy warm morning porridge paired with hot Akara or bean pies.',
                'is_featured': True
            },
            {
                'sku': 'DEV-BKFST-02',
                'name': 'Custard Powder Vanilla Flavour Bucket 2kg',
                'category_slug': 'african-breakfast-foods',
                'price': Decimal('6.50'),
                'compare_at_price': None,
                'stock_quantity': 20,
                'description': 'Rich, aromatic vanilla custard powder packaged in a sturdy reusable bucket. Easy to prepare smooth lump-free breakfast custard enjoyed with sweet milk, honey, and Moin Moin.',
                'is_featured': False
            },
            {
                'sku': 'DEV-BKFST-03',
                'name': 'Milo Cocoa Malt Energy Food Drink 800g',
                'category_slug': 'african-breakfast-foods',
                'price': Decimal('7.99'),
                'compare_at_price': Decimal('8.99'),
                'stock_quantity': 25,
                'description': 'Fortified chocolate malt drink powder packed with Activ-Go, vitamins B2, B6, and calcium. The beloved morning power drink for African children and active adults.',
                'is_featured': False
            },

            # 15. Traditional Food Ingredients
            {
                'sku': 'DEV-TRAD-01',
                'name': 'Ogiri Igbo Fermented Castor Seeds Wrap 100g',
                'category_slug': 'traditional-food-ingredients',
                'price': Decimal('3.20'),
                'compare_at_price': None,
                'stock_quantity': 20,
                'description': 'Traditional fermented castor seed condiment wrapped in dried banana leaves. Delivers that deep, authentic umami depth to Ofe Onugbu, Oha, and native soups.',
                'is_featured': True
            },
            {
                'sku': 'DEV-TRAD-02',
                'name': 'Iru / Dawadawa Fermented Locust Beans 200g',
                'category_slug': 'traditional-food-ingredients',
                'price': Decimal('3.99'),
                'compare_at_price': None,
                'stock_quantity': 28,
                'description': 'Sun-dried whole fermented African locust beans (Parkia biglobosa). Essential for genuine Yoruba Ayamase stew, Efo Riro, and rich vegetable soups.',
                'is_featured': False
            },
            {
                'sku': 'DEV-TRAD-03',
                'name': 'Potash (Kahun / Kaun) Cooking Rock 150g',
                'category_slug': 'traditional-food-ingredients',
                'price': Decimal('2.20'),
                'compare_at_price': None,
                'stock_quantity': 24,
                'description': 'Purified mineral food-grade alkaline rock (Akanwu). Used traditionally to tenderize tough cow leg and beans, and emulsify oil and water in authentic Abacha and Nkwobi sauces.',
                'is_featured': False
            },
        ]

        seeded_count = 0
        for pdata in products_def:
            cat = category_map.get(pdata['category_slug'])
            if not cat:
                self.stdout.write(self.style.WARNING(f"Category slug {pdata['category_slug']} not found!"))
                continue

            product, created = Product.objects.update_or_create(
                sku=pdata['sku'],
                defaults={
                    'name': pdata['name'],
                    'category': cat,
                    'price': pdata['price'],
                    'compare_at_price': pdata.get('compare_at_price'),
                    'stock_quantity': pdata['stock_quantity'],
                    'description': pdata['description'],
                    'is_featured': pdata.get('is_featured', False),
                    'is_active': True,
                }
            )
            seeded_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully synchronized {seeded_count} products across {len(category_map)} categories.'))

        # Check total database counts
        total_cats = Category.objects.filter(is_active=True).count()
        total_prods = Product.objects.filter(is_active=True).count()
        self.stdout.write(f'Active Categories in DB: {total_cats}')
        self.stdout.write(f'Active Products in DB: {total_prods}')
        for cat in Category.objects.filter(is_active=True).order_by('name'):
            p_count = cat.products.filter(is_active=True).count()
            self.stdout.write(f'  - {cat.name} ({cat.slug}): {p_count} products')
