import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import csv

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


f = open("books.csv")
reader = csv.reader(f)


db.execute("CREATE TABLE IF NOT EXISTS books (\
            isbn varchar(15) NOT NULL,\
            title TEXT NOT NULL,\
            author TEXT NOT NULL,\
            year INTEGER NOT NULL,\
            PRIMARY KEY(isbn))")

for isbn, title, author, year in reader:
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", {"isbn": isbn, "title": title, "author":author, "year": year})


db.commit() # transactions are assumed, so close the transaction finished

