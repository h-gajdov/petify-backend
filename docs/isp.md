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

method: `com.petify.petify.service.AuthService.getUserById`
* C1: `userId` is `null`:
  * C1.1: `false`
  * C1.2: `true`
* C2: user exists with `userId`
  * C2.1: `false`
  * C2.2 `true`

| # |  C1  |  C2  | Feasible |
|:-:|:----:|:----:|:--------:|
| 1 | C1.1 | C2.1 |   Yes    |
| 2 | C1.2 | C2.1 |   Yes    |
| 3 | C1.1 | C2.2 |   Yes    |
| 4 | C1.2 | C2.2 |    No    |

method: `com.petify.petify.service.AuthService.getUserByUsername`
* C1: `username` is `null`:
  * C1.1: `false`
  * C1.2: `true`
* C2: user exists with `username`:
  * C2.1: `false`
  * C2.2: `true`

| # |  C1  |  C2  | Feasible |
|:-:|:----:|:----:|:--------:|
| 1 | C1.1 | C2.1 |   Yes    |
| 2 | C1.2 | C2.1 |   Yes    |
| 3 | C1.1 | C2.2 |   Yes    |
| 4 | C1.2 | C2.2 |    No    |

method: `com.petify.petify.service.AuthService.isUserInTopActive`
* C1: `userId` is `null`:
  * C1.1: `false`
  * C1.2: `true`
* C2: outcome of `analyticsRepository.getTopActiveUsers`:
  * C2.1: raises an exception
  * C2.2: returns an empty list
  * C2.3: returns a non-empty list not containing `userId`
  * C2.4: returns a non-empty list containing `userId`

| # |  C1  |  C2  | Feasible |
|:-:|:----:|:----:|:--------:|
| 1 | C1.1 | C2.1 |   Yes    |
| 2 | C1.1 | C2.2 |   Yes    |
| 3 | C1.1 | C2.3 |   Yes    |
| 4 | C1.1 | C2.4 |   Yes    |
| 5 | C1.2 | C2.1 |   Yes    |
| 6 | C1.2 | C2.2 |   Yes    |
| 7 | C1.2 | C2.3 |   Yes    |
| 8 | C1.2 | C2.4 |    No    |

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

