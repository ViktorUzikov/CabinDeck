import sqlite3 as sql


class Database:
    def __init__(self, filename: str):
        self.db = sql.connect(filename)

        self.db.execute('''PRAGMA foreign_keys = ON;''')

        self.db.execute('''CREATE TABLE IF NOT EXISTS flights (
                id integer PRIMARY KEY autoincrement,
                number text NOT NULL,
                departure text NOT NULL,
                arrival text NOT NULL,
                date_time text NOT NULL
        ); ''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS passengers (
                id integer PRIMARY KEY autoincrement,
                flight_id integer NOT NULL references flights(id) on delete cascade,
                full_name text NOT NULL,
                seat text,
                service_class text NOT NULL default 'Эконом',
                photo_path text,
                unique (flight_id, seat)
        );''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS comments (
                id integer PRIMARY KEY autoincrement,
                passenger_id integer NOT NULL references passengers(id) on delete cascade,
                type text NOT NULL check (type in ('warning', 'note')),
                text text NOT NULL,
                created_at text NOT NULL default (datetime('now', 'localtime'))
        );''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS food_items (
                id integer PRIMARY KEY autoincrement,
                name text NOT NULL unique,
                quantity integer NOT NULL,
                min_quantity integer NOT NULL
        );''')
        self.db.execute('create index if not exists idx_passengers_flight on passengers(flight_id);')
        self.db.execute('create index if not exists idx_comments_passenger on comments(passenger_id);')

        self.db.commit()

    def _run(self, sql_script: str, params: tuple = ()):
        ret = self.db.execute(sql_script, params)

        self.db.commit()

        return ret

    def _all(self, sql_script: str, params: tuple = ()):
        return self.db.execute(sql_script, params).fetchall()

    def add_flight(self, number: str, departure: str, arrival: str, date_time: str):
        return self._run(
            'INSERT INTO flights (number, departure, arrival, date_time) VALUES (?, ?, ?, ?)',
            (number, departure, arrival, date_time,),
        ).lastrowid

    def get_flights(self):
        return self._all('SELECT * FROM flights order by date_time desc')

    def get_flight(self, flight_id: int):
        return self.db.execute('SELECT * FROM flights where id = ?', (flight_id,)).fetchone()

    def add_passenger(self, flight_id: int, full_name: str, seat: str, service_class: str, photo_path: str = 'None'):
        return self._run(
            f'INSERT INTO passengers (flight_id, full_name, seat, service_class, photo_path) values (?, ?, ?, ?, ?)',
            (flight_id, full_name, seat, service_class, photo_path)).lastrowid

    def get_passenger(self, passenger_id: int):
        return self.db.execute('SELECT * FROM passengers where id = ?', (passenger_id,)).fetchone()

    def get_passengers(self, flight_id: int):
        return self._all('SELECT * FROM passengers where flight_id = ? order by full_name',
                         (flight_id,))

    def change_passenger(self, passenger_id: int, full_name: str = 'None', seat: str = 'None',
                         service_class: str = 'None', photo_path: str = 'None'):
        fields = {
            'full_name': full_name,
            'seat': seat,
            'service_class': service_class,
            'photo_path': photo_path,
        }

        updates = {col: val for col, val in fields.items() if val != 'None'}

        if not updates:
            return 0

        set_updates = ', '.join(f'{col} = ?' for col in updates)

        return self._run(
            f'UPDATE passengers SET {set_updates} WHERE id = ?',
            (*updates.values(), passenger_id),
        ).rowcount

    def get_passenger_by_seat(self, flight_id: int, seat: str):
        return self.db.execute('SELECT * FROM passengers where flight_id = ? and seat = ?',
                               (flight_id, seat)).fetchone()

    def close(self):
        self.db.close()
