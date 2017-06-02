#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

""" This Python file adds initial data to the database. """

# Python imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from generate_database import Base, User, Catalog, Item

# Connecting to and starting a database session.
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Admin User
adminUser = User(email="user@admin.com")
session.add(adminUser)
session.commit()

# Creating Catalogs and adding them to the database.
catalogs = [Catalog(name="Basketball"), Catalog(name="Baseball"),
            Catalog(name="Boxing"), Catalog(name="Bowling"),
            Catalog(name="Badminton")]
for catalog in catalogs:
    session.add(catalog)
    session.commit()

# Creating Items and adding them to the database.
items = [
         Item(name="Hoop", description="The ball goes in this.",
              catalog=catalogs[0], user=adminUser),
         Item(name="Shoes", description="Gotta love the Jordans.",
              catalog=catalogs[0], user=adminUser),
         Item(name="Bat", description="You hit the ball with this.",
              catalog=catalogs[1], user=adminUser),
         Item(name="Helmet", description="Protects against the balls.",
              catalog=catalogs[1], user=adminUser),
         Item(name="Gloves", description="Helps in punching.",
              catalog=catalogs[2], user=adminUser),
         Item(name="Shorts", description="Shorts!",
              catalog=catalogs[2], user=adminUser),
         Item(name="Pins", description="Gets hit by a ball.",
              catalog=catalogs[3], user=adminUser),
         Item(name="Ball", description="Use to hit the Pins.",
              catalog=catalogs[3], user=adminUser),
         Item(name="Racquet", description="You hit the birdie with this.",
              catalog=catalogs[4], user=adminUser),
         Item(name="Birdie", description="Not a real bird.",
              catalog=catalogs[4], user=adminUser),
              ]
for item in items:
    session.add(item)
    session.commit()
