import gdelt

# Version 1 queries
gd1 = gdelt.gdelt(version=1)

# pull single day, gkg table
results = gd1.Search('2024 Feb 12', table='gkg')
print(len(results))

# pull events table, range, output to json format
results = gd1.Search(['2024 Feb 10', '2024 Feb 12'], coverage=True, table='events')
print(len(results))
