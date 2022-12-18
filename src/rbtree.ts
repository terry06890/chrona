// Copied from node_modules/bintrees/lib/, and adapted to use ES6, classes, and typescript

export class Node<T> {
	data: T;
	left: Node<T> | null;
	right: Node<T> | null;
	red: boolean;
	constructor(data: T){
		this.data = data;
		this.left = null;
		this.right = null;
		this.red = true;
	}
	get_child(dir: boolean){
		return dir ? this.right : this.left;
	}
	set_child(dir: boolean, val: Node<T> | null){
		if (dir) {
			this.right = val;
		}
		else {
			this.left = val;
		}
	}
}

export class Iterator<T> {
	_tree: RBTree<T>;
	_ancestors: Node<T>[];
	_cursor: Node<T> | null;
	constructor(tree: RBTree<T>){
		this._tree = tree;
		this._ancestors = [];
		this._cursor = null;
	}
	data(): T | null {
		return this._cursor !== null ? this._cursor.data : null;
	}
	// if null-iterator, returns first node
	// otherwise, returns next node
	next(): T | null{
		if (this._cursor === null) {
			const root = this._tree._root;
			if (root !== null) {
				this._minNode(root);
			}
		}
		else {
			if(this._cursor.right === null) {
				// no greater node in subtree, go up to parent
				// if coming from a right child, continue up the stack
				let save;
				do {
					save = this._cursor;
					if (this._ancestors.length) {
						this._cursor = this._ancestors.pop()!;
					}
					else {
						this._cursor = null;
						break;
					}
				} while (this._cursor.right === save);
			}
			else {
				// get the next node from the subtree
				this._ancestors.push(this._cursor);
				this._minNode(this._cursor.right);
			}
		}
		return this._cursor !== null ? this._cursor.data : null;
	}
	// if null-iterator, returns last node
	// otherwise, returns previous node
	prev(): T | null {
		if(this._cursor === null) {
			const root = this._tree._root;
			if(root !== null) {
				this._maxNode(root);
			}
		}
		else {
			if(this._cursor.left === null) {
				let save;
				do {
					save = this._cursor;
					if(this._ancestors.length) {
						this._cursor = this._ancestors.pop()!;
					}
					else {
						this._cursor = null;
						break;
					}
				} while(this._cursor.left === save);
			}
			else {
				this._ancestors.push(this._cursor);
				this._maxNode(this._cursor.left);
			}
		}
		return this._cursor !== null ? this._cursor.data : null;
	}
	_minNode(start: Node<T>) {
		while(start.left !== null) {
			this._ancestors.push(start);
			start = start.left;
		}
		this._cursor = start;
	}
	_maxNode(start: Node<T>) {
		while(start.right !== null) {
			this._ancestors.push(start);
			start = start.right;
		}
		this._cursor = start;
	}
}

export class RBTree<T> {
	_root: Node<T> | null;
	size: number;
	_comparator: (a: T, b: T) => number;
	constructor(comparator: (a: T, b: T) => number){
		this._root = null;
		this._comparator = comparator;
		this.size = 0;
	}
	// removes all nodes from the tree
	clear(){
		this._root = null;
		this.size = 0;
	}
	// returns node data if found, null otherwise
	find(data: T): T | null{
		let res = this._root;
		while (res !== null) {
			const c = this._comparator(data, res.data);
			if(c === 0) {
				return res.data;
			}
			else {
				res = res.get_child(c > 0);
			}
		}
		return null;
	}
	// returns iterator to node if found, null otherwise
	findIter(data: T): Iterator<T> | null {
		let res = this._root;
		const iter = this.iterator();
		while(res !== null) {
			const c = this._comparator(data, res.data);
			if(c === 0) {
				iter._cursor = res;
				return iter;
			}
			else {
				iter._ancestors.push(res);
				res = res.get_child(c > 0);
			}
		}
		return null;
	}
	// Returns an iterator to the tree node at or immediately after the item
	lowerBound(item: T): Iterator<T> {
		let cur = this._root;
		const iter = this.iterator();
		const cmp = this._comparator;
		while(cur !== null) {
			const c = cmp(item, cur.data);
			if(c === 0) {
				iter._cursor = cur;
				return iter;
			}
			iter._ancestors.push(cur);
			cur = cur.get_child(c > 0);
		}
		for(let i=iter._ancestors.length - 1; i >= 0; --i) {
			cur = iter._ancestors[i];
			if(cmp(item, cur.data) < 0) {
				iter._cursor = cur;
				iter._ancestors.length = i;
				return iter;
			}
		}
		iter._ancestors.length = 0;
		return iter;
	}
	// Returns an iterator to the tree node immediately after the item
	upperBound(item: T): Iterator<T> {
		const iter = this.lowerBound(item);
		const cmp = this._comparator;
		while(iter.data() !== null && cmp(iter.data()!, item) === 0) {
			iter.next();
		}
		return iter;
	}
	// returns null if tree is empty
	min(): T | null {
		let res = this._root;
		if(res === null) {
			return null;
		}
		while(res.left !== null) {
			res = res.left;
		}
		return res.data;
	}
	// returns null if tree is empty
	max(): T | null {
		let res = this._root;
		if(res === null) {
			return null;
		}
		while(res.right !== null) {
			res = res.right;
		}
		return res.data;
	}
	// returns a null iterator
	// call next() or prev() to point to an element
	iterator() {
		return new Iterator(this);
	}
	// calls cb on each node's data, in order
	each(cb: (x: T) => boolean) {
		const it = this.iterator();
		let data: T | null;
		while((data = it.next()) !== null) {
			if(cb(data) === false) {
				return;
			}
		}
	}
	// calls cb on each node's data, in reverse order
	reach(cb: (x: T) => boolean) {
		const it=this.iterator();
		let data: T | null;
		while((data = it.prev()) !== null) {
			if(cb(data) === false) {
				return;
			}
		}
	}
	// returns true if inserted, false if duplicate
	insert(data: T): boolean {
		let ret = false;
		if(this._root === null) {
			// empty tree
			this._root = new Node(data);
			ret = true;
			this.size++;
		}
		else {
			const head = new Node(undefined) as Node<T>; // fake tree root
			let dir = false;
			let last = false;
			// setup
			let gp: Node<T> | null = null; // grandparent
			let ggp = head; // grand-grand-parent
			let p: Node<T> | null = null; // parent
			let node: Node<T> | null = this._root;
			ggp.right = this._root;
			// search down
			while(true) {
				if(node === null) {
					// insert new node at the bottom
					node = new Node(data);
					p!.set_child(dir, node);
					ret = true;
					this.size++;
				}
				else if(is_red(node.left) && is_red(node.right)) {
					// color flip
					node.red = true;
					node.left!.red = false;
					node.right!.red = false;
				}
				// fix red violation
				if(is_red(node) && is_red(p)) {
					const dir2 = ggp.right === gp;
					if(node === p!.get_child(last)) {
						ggp.set_child(dir2, single_rotate(gp!, !last));
					}
					else {
						ggp.set_child(dir2, double_rotate(gp!, !last));
					}
				}
				const cmp = this._comparator(node.data, data);
				// stop if found
				if(cmp === 0) {
					break;
				}
				last = dir;
				dir = cmp < 0;
				// update helpers
				if(gp !== null) {
					ggp = gp;
				}
				gp = p;
				p = node;
				node = node.get_child(dir);
			}
			// update root
			this._root = head.right;
		}
		// make root black
		this._root!.red = false;
		return ret;
	}
	// returns true if removed, false if not found
	remove(data: T): boolean {
		if(this._root === null) {
			return false;
		}
		const head = new Node(undefined) as Node<T>; // fake tree root
		let node = head;
		node.right = this._root;
		let p: Node<T> | null = null; // parent
		let gp: Node<T> | null = null; // grand parent
		let found: Node<T> | null = null; // found item
		let dir = true;
		while(node.get_child(dir) !== null) {
			const last = dir;
			// update helpers
			gp = p;
			p = node;
			node = node.get_child(dir)!;
			const cmp = this._comparator(data, node.data);
			dir = cmp > 0;
			// save found node
			if (cmp === 0) {
				found = node;
			}
			// push the red node down
			if (!is_red(node) && !is_red(node.get_child(dir))) {
				if(is_red(node.get_child(!dir))) {
					const sr = single_rotate(node, dir);
					p.set_child(last, sr);
					p = sr;
				}
				else if(!is_red(node.get_child(!dir))) {
					const sibling = p.get_child(!last);
					if(sibling !== null) {
						if(!is_red(sibling.get_child(!last)) && !is_red(sibling.get_child(last))) {
							// color flip
							p.red = false;
							sibling.red = true;
							node.red = true;
						}
						else {
							const dir2 = gp!.right === p;
							if(is_red(sibling.get_child(last))) {
								gp!.set_child(dir2, double_rotate(p, last));
							}
							else if(is_red(sibling.get_child(!last))) {
								gp!.set_child(dir2, single_rotate(p, last));
							}
							// ensure correct coloring
							const gpc = gp!.get_child(dir2)!;
							gpc.red = true;
							node.red = true;
							gpc.left!.red = false;
							gpc.right!.red = false;
						}
					}
				}
			}
		}
		// replace and remove if found
		if (found !== null) {
			found.data = node.data;
			p!.set_child(p!.right === node, node.get_child(node.left === null));
			this.size--;
		}
		// update root and make it black
		this._root = head.right;
		if(this._root !== null) {
			this._root.red = false;
		}
		return found !== null;
	}
}

function is_red<T>(node: Node<T> | null): boolean {
	return node !== null && node.red;
}

function single_rotate<T>(root: Node<T>, dir: boolean): Node<T> {
	const save = root.get_child(!dir)!;
	root.set_child(!dir, save.get_child(dir));
	save.set_child(dir, root);
	root.red = true;
	save.red = false;
	return save;
}

function double_rotate<T>(root: Node<T>, dir: boolean): Node<T> {
	root.set_child(!dir, single_rotate(root.get_child(!dir)!, !dir));
	return single_rotate(root, dir);
}

export function rbtree_shallow_copy<T>(tree: RBTree<T>): RBTree<T> {
	const newTree = new RBTree(tree._comparator);
	newTree._root = tree._root;
	newTree.size = tree.size;
	return newTree;
}
