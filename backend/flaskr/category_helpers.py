from flaskr.extensions import pgdb
from dataclasses import dataclass, field
from typing import TypeVar, Iterator, Union, Iterable
from itertools import tee
from functools import lru_cache

@dataclass
class CatNode:
    depth: int
    cat_id: int
    name: str
    show: bool = field(default=False)


T = TypeVar("T")

def tee_lookahead(tee_iterator: Iterator[T], default: T) -> T:
    fork, = tee(tee_iterator, 1)
    return next(fork, default)

CatTree = list[Union[CatNode, 'CatTree']]

def cat_tree_builder(it: Iterator[CatNode],
                     children: CatTree | None = None,
                     depth: int = 0) -> CatTree:
    if not children:
        children = []

    if tee_lookahead(it, CatNode(-1, -1, "placeholder")).depth < depth:
        return children

    for node in it:
        if node.depth == depth:
            children.append(node)
        elif node.depth > depth:
            children.append(cat_tree_builder(it, [node], depth + 1))

        if tee_lookahead(it, CatNode(-1, -1, "placeholder")).depth < depth:
            return children

    return children


def av_categories() -> Iterator[CatNode]:
    with pgdb.get_cursor() as cursor:
        cursor.execute("""
with recursive cat_hierarchy(cat_id, name, parent_cat_id, depth, path) as (
	SELECT cat_id, name, parent_cat_id, 0 as depth, ARRAY[cat_id] from categories where parent_cat_id is null
	union 
	select c.cat_id, c.name, c.parent_cat_id, cat_hierarchy.depth + 1, path || c.cat_id from categories c, cat_hierarchy
	where c.parent_cat_id = cat_hierarchy.cat_id
)
select depth, cat_id, name from cat_hierarchy
order by path
                """)
        [iterator] = tee((CatNode(*row) for row in cursor.fetchall()), 1)
        return iterator

def child_categories(cat: int) -> list[int]:
    with pgdb.get_cursor() as cursor:
        cursor.execute("""
            with recursive child_cats(cat_id, name, parent_cat_id) as (
                select cat_id, name, parent_cat_id
                from categories
                where cat_id=%s
                union
                select c.cat_id, c.name, c.parent_cat_id 
                from categories c, child_cats
                where c.parent_cat_id = child_cats.cat_id
            )
            select cat_id from child_cats
        """, (cat, ))
        if res:=cursor.fetchall():
            return res #type: ignore
        return []



def open_chosen_cat(tree: CatTree, chosen: int) -> bool:
    assert isinstance(tree, list)

    parent = CatNode(-1, -1, "placeholder", False)
    for child in tree:
        if isinstance(child, list):
            if open_chosen_cat(child, chosen):
                parent.show = True
                return True
        else:
            if child.cat_id == chosen:
                parent.show = True
                child.show = True
                return True
            parent = child
    return False
