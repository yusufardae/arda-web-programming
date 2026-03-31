"""
This file is the main Flask backend of my gym project.

Imports I used here:
- date from datetime: to calculate the user's age from date of birth
- Decimal and ROUND_HALF_UP: to calculate money values more safely than normal floats
- Path: to build file paths like the templates folder and .env path
- os: to read environment variables such as database settings
- secrets: to generate random membership IDs in a safer way
- Flask tools: to create routes, render pages, read forms, use sessions and show messages
- werkzeug security helpers: to hash passwords when registering and check them at login
- pymysql: to connect the project to the MySQL database

In short, this file controls the whole flow:
home page -> register -> choose gym plan -> checkout -> membership ID -> login/account.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import os
import secrets

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import pymysql
except ImportError:
    pymysql = None


# I keep common paths and fixed values here so I can reuse them in the whole file.
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'templates'
ZERO_MONEY = Decimal('0.00')
MEMBERSHIP_CODE_DIGITS = 8
MEMBERSHIP_CODE_PREFIXES = {
    'ugym': 'UG',
    'powerzone': 'PW',
}

# This big dictionary is basically the pricing table of the project.
# It stores each club's name, discounts, joining fee, gym packages and extra services.
MEMBERSHIP_PRICING = {
    'ugym': {
        'name': 'uGym',
        'discount_rate_under_26': Decimal('0.20'),
        'joining_fee': Decimal('10.00'),
        'gym_options': {
            'none': {'label': 'No gym membership', 'price': Decimal('0.00')},
            'super_off_peak': {
                'label': 'Gym: Super-off peak (10 am - 12 pm & 2 pm - 4 pm)',
                'price': Decimal('16.00'),
            },
            'off_peak': {
                'label': 'Gym: Off-peak (12 - 2 pm & 8 - 11 pm)',
                'price': Decimal('21.00'),
            },
            'anytime': {'label': 'Gym: Anytime', 'price': Decimal('30.00')},
        },
        'addons': {
            'pool': {
                'label': 'Swimming pool',
                'without_gym': Decimal('25.00'),
                'with_gym': Decimal('15.00'),
                'discountable': True,
            },
            'classes': {
                'label': 'Classes',
                'without_gym': Decimal('20.00'),
                'with_gym': Decimal('10.00'),
                'discountable': True,
            },
            'massage': {
                'label': 'Massage therapy',
                'without_gym': Decimal('30.00'),
                'with_gym': Decimal('25.00'),
                'discountable': False,
            },
            'physiotherapy': {
                'label': 'Physiotherapy',
                'without_gym': Decimal('25.00'),
                'with_gym': Decimal('20.00'),
                'discountable': False,
            },
        },
    },
    'powerzone': {
        'name': 'PowerZone',
        'discount_rate_under_26': Decimal('0.15'),
        'joining_fee': Decimal('30.00'),
        'gym_options': {
            'none': {'label': 'No gym membership', 'price': Decimal('0.00')},
            'super_off_peak': {
                'label': 'Gym: Super-off peak (10 am - 12 pm & 2 pm - 4 pm)',
                'price': Decimal('13.00'),
            },
            'off_peak': {
                'label': 'Gym: Off-peak (12 - 2 pm & 8 - 11 pm)',
                'price': Decimal('19.00'),
            },
            'anytime': {'label': 'Gym: Anytime', 'price': Decimal('24.00')},
        },
        'addons': {
            'pool': {
                'label': 'Swimming pool',
                'without_gym': Decimal('20.00'),
                'with_gym': Decimal('12.50'),
                'discountable': True,
            },
            'classes': {
                'label': 'Classes',
                'without_gym': Decimal('20.00'),
                'with_gym': Decimal('0.00'),
                'discountable': True,
            },
            'massage': {
                'label': 'Massage therapy',
                'without_gym': Decimal('30.00'),
                'with_gym': Decimal('25.00'),
                'discountable': False,
            },
            'physiotherapy': {
                'label': 'Physiotherapy',
                'without_gym': Decimal('30.00'),
                'with_gym': Decimal('25.00'),
                'discountable': False,
            },
        },
    },
}


def money(value):
    # I round every money value to 2 decimals so prices stay consistent.
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def money_to_float(value):
    # Templates and some calculations are easier to show with normal float values.
    return float(money(value))


def load_env_file(env_path):
    # This reads the local .env file manually and loads settings like DB host/user/password.
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# I load .env before creating the app config so custom settings are available.
load_env_file(BASE_DIR / '.env')

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='',
)

# These values are used while connecting to MySQL and managing sessions.
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'change-this-secret-key'),
    MYSQL_HOST=os.getenv('MYSQL_HOST', '127.0.0.1'),
    MYSQL_USER=os.getenv('MYSQL_USER', 'root'),
    MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD', ''),
    MYSQL_DATABASE=os.getenv('MYSQL_DATABASE', 'mars_gym'),
    MYSQL_PORT=int(os.getenv('MYSQL_PORT', '3306')),
)


def get_mysql_connection():
    # All database operations use this helper so the connection settings stay in one place.
    if pymysql is None:
        raise RuntimeError(
            'PyMySQL is not installed. Run `pip install PyMySQL` in your virtual environment.'
        )

    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        port=app.config['MYSQL_PORT'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DATABASE'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def ensure_database_tables():
    # I call this before DB actions to make sure the needed tables/columns already exist.
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    surname VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    telephone VARCHAR(30) NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    date_of_birth DATE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    terms_accepted TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS membership_selections (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    club VARCHAR(30) NOT NULL,
                    gym_access VARCHAR(30) NOT NULL,
                    pool_selected TINYINT(1) NOT NULL DEFAULT 0,
                    classes_selected TINYINT(1) NOT NULL DEFAULT 0,
                    massage_selected TINYINT(1) NOT NULL DEFAULT 0,
                    physiotherapy_selected TINYINT(1) NOT NULL DEFAULT 0,
                    joining_fee DECIMAL(10, 2) NOT NULL,
                    gym_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    pool_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    classes_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    massage_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    physiotherapy_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    discount_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
                    discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    total_price DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_membership_user
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                '''
            )
            cursor.execute(
                '''
                SELECT CHARACTER_MAXIMUM_LENGTH AS code_length
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'membership_selections'
                  AND COLUMN_NAME = 'membership_code'
                ''',
                (app.config['MYSQL_DATABASE'],),
            )
            column_info = cursor.fetchone()
            if not column_info:
                cursor.execute(
                    '''
                    ALTER TABLE membership_selections
                    ADD COLUMN membership_code VARCHAR(10) NULL UNIQUE
                    '''
                )
            elif (column_info.get('code_length') or 0) < 10:
                cursor.execute(
                    '''
                    ALTER TABLE membership_selections
                    MODIFY COLUMN membership_code VARCHAR(10) NULL
                    '''
                )
        connection.commit()
    finally:
        connection.close()


def calculate_age(birth_date, on_date=None):
    # This calculates age correctly by also checking if the birthday has happened this year.
    today = on_date or date.today()
    age = today.year - birth_date.year

    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age


def get_registration_redirect_endpoint(age):
    # After registration, older users go to PowerZone and the others go to uGym.
    if age >= 66:
        return 'marspower'

    return 'marsugym'


def validate_registration_form(form_data):
    # Here I validate the registration form before writing anything into the database.
    required_fields = {
        'name': 'Name',
        'surname': 'Surname',
        'password': 'Password',
        'password2': 'Confirm Password',
        'gender': 'Gender',
        'dateofbirth': 'Date of Birth',
        'email': 'Email',
        'telephone': 'Telephone',
    }

    # I strip text fields first so spaces do not count as valid input.
    cleaned_data = {field: form_data.get(field, '').strip() for field in required_fields}
    missing_fields = [label for field, label in required_fields.items() if not cleaned_data[field]]
    if missing_fields:
        raise ValueError(f"Please fill in all required fields: {', '.join(missing_fields)}")

    if cleaned_data['password'] != cleaned_data['password2']:
        raise ValueError('Passwords do not match.')

    # If the date format is wrong, registration should stop here.
    try:
        birth_date = date.fromisoformat(cleaned_data['dateofbirth'])
    except ValueError as exc:
        raise ValueError('Date of birth is invalid.') from exc

    age = calculate_age(birth_date)
    # The project rule is that users under 16 cannot register.
    if age < 16:
        raise ValueError('Users under 16 cannot register.')

    if not form_data.get('terms_conditions'):
        raise ValueError('You must accept the Terms and Conditions to continue.')

    # I return the cleaned version of the data so later functions can directly save it.
    return {
        'name': cleaned_data['name'],
        'surname': cleaned_data['surname'],
        'email': cleaned_data['email'],
        'telephone': cleaned_data['telephone'],
        'gender': cleaned_data['gender'],
        'date_of_birth': birth_date,
        'password_hash': generate_password_hash(cleaned_data['password']),
        'terms_accepted': 1,
        'age': age,
    }


def save_user(user_data):
    # This inserts a new user into the users table and returns the new user id.
    ensure_database_tables()

    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO users (
                    name,
                    surname,
                    email,
                    telephone,
                    gender,
                    date_of_birth,
                    password_hash,
                    terms_accepted
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    user_data['name'],
                    user_data['surname'],
                    user_data['email'],
                    user_data['telephone'],
                    user_data['gender'],
                    user_data['date_of_birth'],
                    user_data['password_hash'],
                    user_data['terms_accepted'],
                ),
            )
            user_id = cursor.lastrowid
        connection.commit()
        return user_id
    finally:
        connection.close()


def get_user_by_email(email):
    # I use this during login to find the correct user record.
    ensure_database_tables()

    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT *
                FROM users
                WHERE email = %s
                ''',
                (email,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def calculate_membership_pricing(club_key, age, form_data, require_selection=True):
    # This is one of the main functions: it calculates the total membership price.
    club = MEMBERSHIP_PRICING[club_key]
    gym_access = form_data.get('gym_access', 'none')
    if gym_access not in club['gym_options']:
        raise ValueError('Please select a valid gym package.')

    # These booleans tell me which extras the user selected.
    include_pool = bool(form_data.get('include_pool'))
    include_classes = bool(form_data.get('include_classes'))
    include_massage = bool(form_data.get('include_massage'))
    include_physiotherapy = bool(form_data.get('include_physiotherapy'))
    has_gym_membership = gym_access != 'none'

    # If nothing is selected, I show an error instead of saving an empty membership.
    if require_selection and not any(
        [has_gym_membership, include_pool, include_classes, include_massage, include_physiotherapy]
    ):
        raise ValueError('Please select at least one membership or extra service.')

    # Some extras are cheaper when the user already has a gym package, so I check both cases.
    gym_fee = club['gym_options'][gym_access]['price']
    pool_fee = (
        club['addons']['pool']['with_gym'] if include_pool and has_gym_membership
        else club['addons']['pool']['without_gym'] if include_pool
        else ZERO_MONEY
    )
    classes_fee = (
        club['addons']['classes']['with_gym'] if include_classes and has_gym_membership
        else club['addons']['classes']['without_gym'] if include_classes
        else ZERO_MONEY
    )
    massage_fee = (
        club['addons']['massage']['with_gym'] if include_massage and has_gym_membership
        else club['addons']['massage']['without_gym'] if include_massage
        else ZERO_MONEY
    )
    physiotherapy_fee = (
        club['addons']['physiotherapy']['with_gym'] if include_physiotherapy and has_gym_membership
        else club['addons']['physiotherapy']['without_gym'] if include_physiotherapy
        else ZERO_MONEY
    )

    # Under-26 discount only applies to gym, pool and classes in this project.
    joining_fee = club['joining_fee']
    discount_rate = club['discount_rate_under_26'] if age <= 25 else ZERO_MONEY
    discountable_total = gym_fee + pool_fee + classes_fee
    discount_amount = money(discountable_total * discount_rate)
    total_price = money(
        joining_fee
        + gym_fee
        + pool_fee
        + classes_fee
        + massage_fee
        + physiotherapy_fee
        - discount_amount
    )

    # I return all price details because later pages need a full breakdown, not just the total.
    return {
        'club': club_key,
        'club_name': club['name'],
        'gym_access': gym_access,
        'gym_access_label': club['gym_options'][gym_access]['label'],
        'pool_selected': include_pool,
        'classes_selected': include_classes,
        'massage_selected': include_massage,
        'physiotherapy_selected': include_physiotherapy,
        'joining_fee': joining_fee,
        'gym_fee': gym_fee,
        'pool_fee': pool_fee,
        'classes_fee': classes_fee,
        'massage_fee': massage_fee,
        'physiotherapy_fee': physiotherapy_fee,
        'discount_rate': discount_rate,
        'discount_rate_percent': int(discount_rate * 100),
        'discount_amount': discount_amount,
        'discount_eligible': age <= 25,
        'total_price': total_price,
    }


def save_membership_selection(user_id, selection):
    # This saves the user's chosen plan. If they already had one, it updates the same row.
    ensure_database_tables()

    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO membership_selections (
                    user_id,
                    club,
                    gym_access,
                    pool_selected,
                    classes_selected,
                    massage_selected,
                    physiotherapy_selected,
                    joining_fee,
                    gym_fee,
                    pool_fee,
                    classes_fee,
                    massage_fee,
                    physiotherapy_fee,
                    discount_rate,
                    discount_amount,
                    total_price
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    club = VALUES(club),
                    gym_access = VALUES(gym_access),
                    pool_selected = VALUES(pool_selected),
                    classes_selected = VALUES(classes_selected),
                    massage_selected = VALUES(massage_selected),
                    physiotherapy_selected = VALUES(physiotherapy_selected),
                    joining_fee = VALUES(joining_fee),
                    gym_fee = VALUES(gym_fee),
                    pool_fee = VALUES(pool_fee),
                    classes_fee = VALUES(classes_fee),
                    massage_fee = VALUES(massage_fee),
                    physiotherapy_fee = VALUES(physiotherapy_fee),
                    discount_rate = VALUES(discount_rate),
                    discount_amount = VALUES(discount_amount),
                    total_price = VALUES(total_price)
                ''',
                (
                    user_id,
                    selection['club'],
                    selection['gym_access'],
                    int(selection['pool_selected']),
                    int(selection['classes_selected']),
                    int(selection['massage_selected']),
                    int(selection['physiotherapy_selected']),
                    selection['joining_fee'],
                    selection['gym_fee'],
                    selection['pool_fee'],
                    selection['classes_fee'],
                    selection['massage_fee'],
                    selection['physiotherapy_fee'],
                    selection['discount_rate'],
                    selection['discount_amount'],
                    selection['total_price'],
                ),
            )
            cursor.execute(
                'SELECT id FROM membership_selections WHERE user_id = %s',
                (user_id,),
            )
            saved_selection = cursor.fetchone()
        connection.commit()
        return saved_selection['id']
    finally:
        connection.close()


def get_membership_selection(user_id):
    # This gets the saved membership information of the logged-in user.
    ensure_database_tables()

    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT *
                FROM membership_selections
                WHERE user_id = %s
                ''',
                (user_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def membership_code_exists(cursor, membership_code):
    # Before creating a membership code, I check if it is already used.
    cursor.execute(
        '''
        SELECT id
        FROM membership_selections
        WHERE membership_code = %s
        ''',
        (membership_code,),
    )
    return cursor.fetchone() is not None


def get_membership_code_prefix(club_key):
    # Each club has its own prefix so the ID also shows which club it belongs to.
    if club_key not in MEMBERSHIP_CODE_PREFIXES:
        raise ValueError('A valid club could not be found for the membership ID.')
    return MEMBERSHIP_CODE_PREFIXES[club_key]


def membership_code_matches_club(membership_code, club_key):
    # This prevents a wrong prefix like PW being used for a uGym member.
    normalized_code = normalize_membership_code(membership_code)
    if not normalized_code:
        return False
    return normalized_code.startswith(get_membership_code_prefix(club_key))


def generate_unique_membership_code(cursor, club_key):
    # I generate a random code and retry a few times until I get a unique one.
    prefix = get_membership_code_prefix(club_key)
    for _ in range(20):
        membership_code = f'{prefix}{secrets.randbelow(100_000_000):0{MEMBERSHIP_CODE_DIGITS}d}'
        if not membership_code_exists(cursor, membership_code):
            return membership_code

    raise RuntimeError('A unique membership ID could not be created. Please try again.')


def ensure_membership_code_for_user(user_id):
    # If the user already has a correct code, I keep it. Otherwise I create a new one.
    ensure_database_tables()

    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT membership_code, club
                FROM membership_selections
                WHERE user_id = %s
                ''',
                (user_id,),
            )
            selection = cursor.fetchone()
            if not selection:
                raise ValueError('You must choose a membership before a membership ID can be created.')

            club_key = selection.get('club')
            current_code = selection.get('membership_code')
            if current_code and membership_code_matches_club(current_code, club_key):
                return normalize_membership_code(current_code)

            membership_code = generate_unique_membership_code(cursor, club_key)
            cursor.execute(
                '''
                UPDATE membership_selections
                SET membership_code = %s
                WHERE user_id = %s
                ''',
                (membership_code, user_id),
            )
        connection.commit()
        return membership_code
    finally:
        connection.close()


def normalize_membership_code(raw_value):
    # This cleans the searched code and checks the expected format like UG12345678.
    cleaned = (raw_value or '').strip().replace('#', '').upper()
    if len(cleaned) != MEMBERSHIP_CODE_DIGITS + 2:
        return None

    prefix = cleaned[:2]
    digits = cleaned[2:]

    if prefix not in MEMBERSHIP_CODE_PREFIXES.values():
        return None
    if len(digits) != MEMBERSHIP_CODE_DIGITS or not digits.isdigit():
        return None
    return cleaned


def get_membership_by_code(membership_code):
    # This is used on the account page to search a membership by its ID.
    ensure_database_tables()

    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT ms.*, u.name, u.surname
                FROM membership_selections ms
                JOIN users u ON u.id = ms.user_id
                WHERE ms.membership_code = %s
                ''',
                (membership_code,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def build_membership_label(selection):
    # I build a readable text label so the account/checkout page can show the chosen package nicely.
    club = MEMBERSHIP_PRICING.get(selection['club'], {})
    club_name = club.get('name', selection['club'])
    extras = []

    if selection.get('pool_selected'):
        extras.append('Swimming pool')
    if selection.get('classes_selected'):
        extras.append('Classes')
    if selection.get('massage_selected'):
        extras.append('Massage therapy')
    if selection.get('physiotherapy_selected'):
        extras.append('Physiotherapy')

    if selection.get('gym_access') and selection['gym_access'] != 'none':
        gym_options = club.get('gym_options', {})
        gym_label = gym_options.get(selection['gym_access'], {}).get('label', selection['gym_access'])
        membership_label = f'{club_name} - {gym_label}'
        if extras:
            membership_label = f"{membership_label} | Extras: {', '.join(extras)}"
        return membership_label

    if extras:
        return f"{club_name} - {', '.join(extras)}"

    return club_name


def build_club_context(club_key, age):
    # This prepares all club data in a template-friendly way for the plan selection pages.
    club = MEMBERSHIP_PRICING[club_key]
    gym_options = [
        {
            'key': key,
            'label': option['label'],
            'price': money_to_float(option['price']),
        }
        for key, option in club['gym_options'].items()
    ]
    addon_items = []
    # These rows are only for display, so the HTML page can print the pricing table easily.
    pricing_rows = [
        {
            'label': 'Joining fee (one-off fee)',
            'price_label': f"{money_to_float(club['joining_fee']):.2f}",
        }
    ]

    for key, addon in club['addons'].items():
        addon_items.append(
            {
                'key': key,
                'label': addon['label'],
                'description': (
                    f"Without gym: {money_to_float(addon['without_gym']):.2f} / "
                    f"With gym: +{money_to_float(addon['with_gym']):.2f}"
                ),
            }
        )

    for key, option in club['gym_options'].items():
        if key == 'none':
            continue
        pricing_rows.append(
            {
                'label': option['label'],
                'price_label': f"{money_to_float(option['price']):.2f}",
            }
        )

    pricing_rows.extend(
        [
            {
                'label': 'Swimming pool (without gym m.)',
                'price_label': f"{money_to_float(club['addons']['pool']['without_gym']):.2f}",
            },
            {
                'label': 'Swimming pool (with gym m.)',
                'price_label': f"+{money_to_float(club['addons']['pool']['with_gym']):.2f} extra",
            },
            {
                'label': 'Classes (without gym m.)',
                'price_label': f"{money_to_float(club['addons']['classes']['without_gym']):.2f}",
            },
            {
                'label': 'Classes (with gym m.)',
                'price_label': f"+{money_to_float(club['addons']['classes']['with_gym']):.2f} extra",
            },
            {
                'label': 'Massage therapy (without gym m.)',
                'price_label': f"{money_to_float(club['addons']['massage']['without_gym']):.2f}",
            },
            {
                'label': 'Massage therapy (with gym m.)',
                'price_label': f"+{money_to_float(club['addons']['massage']['with_gym']):.2f} extra",
            },
            {
                'label': 'Physiotherapy (without gym m.)',
                'price_label': f"{money_to_float(club['addons']['physiotherapy']['without_gym']):.2f}",
            },
            {
                'label': 'Physiotherapy (with gym m.)',
                'price_label': f"+{money_to_float(club['addons']['physiotherapy']['with_gym']):.2f} extra",
            },
        ]
    )

    # I also send live pricing data so the template/JS can update totals on the page.
    return {
        'key': club_key,
        'name': club['name'],
        'gym_options': gym_options,
        'addons': addon_items,
        'pricing_rows': pricing_rows,
        'discount_copy': (
            f"If you are 25 or younger, {club['name']} applies "
            f"{int(club['discount_rate_under_26'] * 100)}% off gym, pool and classes. "
            'Joining fee, massage and physiotherapy stay at full price.'
        ),
        'discount_eligible': age <= 25,
        'live_pricing': {
            'joining_fee': money_to_float(club['joining_fee']),
            'discount_rate_under_26': money_to_float(club['discount_rate_under_26']),
            'gym_options': {
                key: money_to_float(option['price']) for key, option in club['gym_options'].items()
            },
            'addons': {
                key: {
                    'without_gym': money_to_float(addon['without_gym']),
                    'with_gym': money_to_float(addon['with_gym']),
                    'discountable': addon['discountable'],
                }
                for key, addon in club['addons'].items()
            },
        },
    }


def pricing_to_template(pricing):
    # This converts Decimal values into simpler values that are easier to render in HTML.
    return {
        'club_name': pricing['club_name'],
        'gym_access': pricing['gym_access'],
        'gym_access_label': pricing['gym_access_label'],
        'pool_selected': pricing['pool_selected'],
        'classes_selected': pricing['classes_selected'],
        'massage_selected': pricing['massage_selected'],
        'physiotherapy_selected': pricing['physiotherapy_selected'],
        'joining_fee': money_to_float(pricing['joining_fee']),
        'gym_fee': money_to_float(pricing['gym_fee']),
        'pool_fee': money_to_float(pricing['pool_fee']),
        'classes_fee': money_to_float(pricing['classes_fee']),
        'massage_fee': money_to_float(pricing['massage_fee']),
        'physiotherapy_fee': money_to_float(pricing['physiotherapy_fee']),
        'discount_rate_percent': pricing['discount_rate_percent'],
        'discount_amount': money_to_float(pricing['discount_amount']),
        'discount_eligible': pricing['discount_eligible'],
        'total_price': money_to_float(pricing['total_price']),
    }


def build_checkout_context(selection):
    # This creates the checkout summary list the user sees before finishing.
    club = MEMBERSHIP_PRICING[selection['club']]
    items = [
        {'label': 'Joining fee (one-off fee)', 'amount': money_to_float(selection['joining_fee'])}
    ]

    if selection['gym_access'] != 'none':
        items.append(
            {
                'label': club['gym_options'][selection['gym_access']]['label'],
                'amount': money_to_float(selection['gym_fee']),
            }
        )

    if selection['pool_selected']:
        items.append({'label': 'Swimming pool', 'amount': money_to_float(selection['pool_fee'])})
    if selection['classes_selected']:
        items.append({'label': 'Classes', 'amount': money_to_float(selection['classes_fee'])})
    if selection['massage_selected']:
        items.append({'label': 'Massage therapy', 'amount': money_to_float(selection['massage_fee'])})
    if selection['physiotherapy_selected']:
        items.append(
            {'label': 'Physiotherapy', 'amount': money_to_float(selection['physiotherapy_fee'])}
        )

    # Subtotal is the sum before discount, then total_price is the final amount after discount.
    subtotal = sum(item['amount'] for item in items)
    return {
        'club_name': club['name'],
        'line_items': items,
        'subtotal': subtotal,
        'discount_amount': money_to_float(selection['discount_amount']),
        'discount_rate_percent': int(money(selection['discount_rate']) * 100),
        'has_discount': money(selection['discount_amount']) > ZERO_MONEY,
        'total_price': money_to_float(selection['total_price']),
    }


def render_membership_builder(club_key, template_name):
    # I reuse the same logic for both clubs instead of writing two separate long route functions.
    user_id = session.get('user_id')
    user_age = session.get('user_age')

    # If the user did not register yet, they should not access plan selection directly.
    if not user_id or user_age is None:
        flash('You must register before continuing.', 'danger')
        return redirect(url_for('joinus'))

    form_data = request.form.to_dict() if request.method == 'POST' else {}

    # Even before form submit, I prepare a preview so the page can show prices immediately.
    try:
        price_preview = calculate_membership_pricing(
            club_key,
            int(user_age),
            form_data,
            require_selection=False,
        )
    except ValueError:
        price_preview = calculate_membership_pricing(club_key, int(user_age), {}, require_selection=False)

    # On POST, the selected plan is validated and then saved to the database.
    if request.method == 'POST':
        try:
            selection = calculate_membership_pricing(club_key, int(user_age), request.form)
            selection_id = save_membership_selection(user_id, selection)
            session['membership_selection_id'] = selection_id
            session['selected_club'] = club_key
            return redirect(url_for('checkout'))
        except ValueError as exc:
            flash(str(exc), 'danger')
        except RuntimeError as exc:
            flash(str(exc), 'danger')
        except Exception as exc:
            app.logger.exception('Membership selection could not be saved.')
            flash(f'Membership selection could not be saved. Details: {exc}', 'danger')

    return render_template(
        template_name,
        club=build_club_context(club_key, int(user_age)),
        form_data=form_data,
        price_preview=pricing_to_template(price_preview),
        user_age=int(user_age),
    )


@app.route('/')
def index():
    # Home page route.
    return render_template('index.html')


@app.route('/joinus', methods=['GET', 'POST'])
def joinus():
    # This route handles both showing the registration form and submitting it.
    form_data = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()

        # If validation passes, I save the user and keep basic info in session.
        try:
            user_data = validate_registration_form(request.form)
            user_id = save_user(user_data)
            session['user_id'] = user_id
            session['user_age'] = user_data['age']
            session['user_name'] = user_data['name']
            session.pop('membership_selection_id', None)
            session.pop('selected_club', None)
            redirect_endpoint = get_registration_redirect_endpoint(user_data['age'])
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('marsrgstr.html', form_data=form_data), 400
        except RuntimeError as exc:
            flash(str(exc), 'danger')
            return render_template('marsrgstr.html', form_data=form_data), 500
        except Exception as exc:
            if pymysql is not None and isinstance(exc, pymysql.err.IntegrityError):
                flash('An account already exists with this email address.', 'danger')
                return render_template('marsrgstr.html', form_data=form_data), 409

            if pymysql is not None and isinstance(exc, pymysql.err.OperationalError):
                flash(
                    'Could not connect to MySQL. Details: '
                    f'{exc}. Run `database/schema.sql` in Workbench, '
                    'then use the same MYSQL_HOST=127.0.0.1, MYSQL_PORT=3306, '
                    'MYSQL_USER and MYSQL_PASSWORD values in `.env`.',
                    'danger',
                )
                return render_template('marsrgstr.html', form_data=form_data), 500

            app.logger.exception('Registration data could not be written to the MySQL table.')
            flash('An unexpected database error occurred during registration.', 'danger')
            return render_template('marsrgstr.html', form_data=form_data), 500

        # After registration, the next page depends on age.
        flash('Registration completed successfully. You can now continue to gym selection.', 'success')
        return redirect(url_for(redirect_endpoint))

    return render_template('marsrgstr.html', form_data=form_data)


@app.route('/marsugym')
def marsugym():
    # Intro page for uGym.
    return render_template('marsrgstr3.html')


@app.route('/marspower')
def marspower():
    # Intro page for PowerZone.
    return render_template('marsrgstr4.html')


@app.route('/uGym', methods=['GET', 'POST'])
def uGym():
    # uGym plan selection page.
    return render_membership_builder('ugym', 'marsplan3.html')


@app.route('/PowerZone', methods=['GET', 'POST'])
def PowerZone():
    # PowerZone plan selection page.
    return render_membership_builder('powerzone', 'marsplan4.html')


@app.route('/checkout')
def checkout():
    # This page shows the final price breakdown before payment is completed.
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to register before checkout.', 'danger')
        return redirect(url_for('joinus'))

    selection = get_membership_selection(user_id)
    if not selection:
        flash('You need to choose a membership before checkout.', 'danger')
        next_step = session.get('selected_club')
        if next_step == 'powerzone':
            return redirect(url_for('PowerZone'))
        return redirect(url_for('uGym'))

    return render_template('marscheckout.html', checkout=build_checkout_context(selection))


@app.route('/checkoutcomplete')
def checkoutcomplete():
    # After checkout, I generate/show the membership ID and selected package summary.
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to reach the payment-complete step before viewing your membership ID.', 'danger')
        return redirect(url_for('joinus'))

    try:
        membership_code = ensure_membership_code_for_user(user_id)
        selection = get_membership_selection(user_id)
    except ValueError as exc:
        flash(str(exc), 'danger')
        next_step = session.get('selected_club')
        if next_step == 'powerzone':
            return redirect(url_for('PowerZone'))
        return redirect(url_for('uGym'))
    except Exception as exc:
        app.logger.exception('Membership code could not be created.')
        flash(f'Membership ID could not be created. Details: {exc}', 'danger')
        return redirect(url_for('checkout'))

    session['membership_code'] = membership_code
    return render_template(
        'marscheckoutcomplete.html',
        membership_code=membership_code,
        membership_label=build_membership_label(selection),
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    # This route logs the user in by checking email and hashed password.
    form_data = {}

    if request.method == 'POST':
        form_data = {'email': request.form.get('email', '').strip()}
        password = request.form.get('password', '')

        if not form_data['email'] or not password:
            flash('Please fill in the email and password fields.', 'danger')
            return render_template('marslogin.html', form_data=form_data), 400

        try:
            user = get_user_by_email(form_data['email'])
        except RuntimeError as exc:
            flash(str(exc), 'danger')
            return render_template('marslogin.html', form_data=form_data), 500
        except Exception as exc:
            if pymysql is not None and isinstance(exc, pymysql.err.OperationalError):
                flash(
                    'Could not connect to MySQL for login. '
                    f'Details: {exc}',
                    'danger',
                )
                return render_template('marslogin.html', form_data=form_data), 500

            app.logger.exception('The user record could not be read during login.')
            flash('An unexpected database error occurred during login.', 'danger')
            return render_template('marslogin.html', form_data=form_data), 500

        # Passwords are not stored as plain text, so I compare with the hash here.
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Email or password is incorrect.', 'danger')
            return render_template('marslogin.html', form_data=form_data), 401

        birth_date = user.get('date_of_birth')
        if isinstance(birth_date, str):
            birth_date = date.fromisoformat(birth_date)

        session['user_id'] = user['id']
        session['user_name'] = user.get('name', 'USER')
        session['user_age'] = calculate_age(birth_date) if birth_date else None

        # If the user already chose a membership before, I reload it into the session.
        try:
            selection = get_membership_selection(user['id'])
        except Exception:
            app.logger.exception('Membership selection could not be read after login.')
            selection = None

        if selection:
            session['membership_selection_id'] = selection.get('id')
            session['selected_club'] = selection.get('club')
            membership_code = selection.get('membership_code')
            if membership_code and not membership_code_matches_club(
                membership_code,
                selection.get('club'),
            ):
                try:
                    membership_code = ensure_membership_code_for_user(user['id'])
                except Exception:
                    app.logger.exception('Membership ID could not be refreshed during login.')
                    membership_code = None

            if membership_code:
                session['membership_code'] = membership_code
            else:
                session.pop('membership_code', None)
        else:
            session.pop('membership_selection_id', None)
            session.pop('selected_club', None)
            session.pop('membership_code', None)

        flash('Login successful.', 'success')
        return redirect(url_for('account'))

    return render_template('marslogin.html', form_data=form_data)


@app.route('/account', methods=['GET', 'POST'])
def account():
    # On the account page, the user can see their info and also search membership IDs.
    current_user_name = session.get('user_name', 'USER')
    current_membership_code = session.get('membership_code')
    membership_result = None
    searched_membership_code = ''

    if session.get('user_id'):
        current_selection = get_membership_selection(session['user_id'])
        if current_selection:
            current_membership_code = current_selection.get('membership_code') or current_membership_code
            if current_membership_code and not membership_code_matches_club(
                current_membership_code,
                current_selection.get('club'),
            ):
                try:
                    current_membership_code = ensure_membership_code_for_user(session['user_id'])
                    session['membership_code'] = current_membership_code
                except Exception:
                    app.logger.exception('Membership ID could not be refreshed on the account page.')

    # When the search form is submitted, I normalize the code first and then query the DB.
    if request.method == 'POST':
        searched_membership_code = request.form.get('membership_code', '')
        normalized_code = normalize_membership_code(searched_membership_code)

        if not normalized_code:
            flash('Please enter a valid membership ID starting with UG or PW.', 'danger')
        else:
            result = get_membership_by_code(normalized_code)
            if not result:
                flash('No record matched that membership ID.', 'danger')
            else:
                membership_result = build_membership_label(result)
                current_user_name = result.get('name', current_user_name)
                current_membership_code = result.get('membership_code', current_membership_code)

    return render_template(
        'marsaccount.html',
        current_user_name=current_user_name,
        current_membership_code=current_membership_code,
        membership_result=membership_result,
        searched_membership_code=searched_membership_code,
    )


if __name__ == '__main__':
    # I run the app in debug mode while developing the project locally.
    app.run(debug=True, port=5001)
