def to_vector(embedding):
    """Render an embedding as a pgvector literal, e.g. "[0.1,0.2,0.3]".

    psycopg2 adapts a Python list to a Postgres array, and there is no `<->`
    operator between `vector` and `double precision[]`. Sending the literal and
    casting it with `%s::vector` is what lets the comparison resolve.
    """
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"
