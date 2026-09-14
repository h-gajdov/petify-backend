# ISP TESTS

---

### All Combinations Coverage (ACoC)
**Method**: `com.petify.petify.service.FavoriteService.getFavoritedListings`

Partitions:
* C1: `userId` is `null`
  * C1.1: `false`
  * C1.2: `true`
* C2: `userId` is:
  * C2.1: less than 0
  * C2.2: 0
  * C2.3: greater than 0

| # |  C1  |  C2  | Feasible |
|:-:|:----:|:----:|:--------:|
| 1 | C1.1 | C2.1 |   Yes    |
| 2 | C1.1 | C2.2 |   Yes    | 
| 3 | C1.1 | C2.3 |   Yes    |
| 4 | C1.2 | C2.1 |    No    |
| 5 | C1.2 | C2.2 |    No    |
| 6 | C1.2 | C2.3 |    No    |

### Base Choice Coverage (BCC)
method: `com.petify.petify.service.FavoriteService.addFavorite`

Partitions:
* C1: `userId` is `null`
  * C1.1: `false`
  * C1.2: `true`
* C2: `userId` is:
  * C2.1: less than 0
  * C2.2: 0
  * C2.3: greater than 0
* C3: `listingId` is `null`
    * C3.1: `false`
    * C3.2: `true`
* C4: `listingId` is:
    * C4.1: less than 0
    * C4.2: 0
    * C4.3: greater than 0

| # |  C1  |  C2  | C3   | C4   | Feasible |
|:-:|:----:|:----:|------|------|:--------:|
| 1 | C1.1 | C2.3 | C3.1 | C4.3 |   Yes    |
| 2 | C1.2 | C2.3 | C3.1 | C4.3 |    No    |
| 3 | C1.1 | C2.2 | C3.1 | C4.3 |   Yes    |
| 4 | C1.1 | C2.1 | C3.1 | C4.3 |   Yes    |
| 5 | C1.1 | C2.3 | C3.2 | C4.3 |    No    |
| 6 | C1.1 | C2.3 | C3.1 | C4.2 |   Yes    |
| 7 | C1.1 | C2.3 | C3.1 | C4.1 |   Yes    |

