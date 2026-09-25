-- V2 inserts reviews with explicit ids, which leaves the sequence behind them.
SELECT setval(pg_get_serial_sequence('reviews', 'review_id'), (SELECT MAX(review_id) FROM reviews));
