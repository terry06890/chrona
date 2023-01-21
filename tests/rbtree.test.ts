import {RBTree, Iterator, rbtree_shallow_copy} from '/src/rbtree.ts'

function cmpInt(a: int, b: int){
	return a - b;
}

function getIteratorEls<T>(itr: Iterator<T>): T[]{
	let els: T[] = [];
	if (itr.data() != null){
		els.push(itr.data());
	}
	let el: T | null;
	while ((el = itr.next()) != null){
		els.push(el);
	}
	return els;
}

function getIteratorElsRev<T>(itr: Iterator<T>): T[]{
	let els: T[] = [];
	if (itr.data() != null){
		els.push(itr.data());
	}
	let el: T | null;
	while ((el = itr.prev()) != null){
		els.push(el);
	}
	return els;
}

test('insert and remove', () => {
	let tree = new RBTree(cmpInt);
	expect(tree.insert(10)).toBe(true);
	expect(tree.insert(10)).toBe(false);
	expect(tree.insert(20)).toBe(true);
	expect(tree.insert(-1)).toBe(true);
	//
	expect(tree.remove(100)).toBe(false);
	expect(tree.remove(10)).toBe(true);
	//
	expect(tree.size).toBe(2);
	expect(tree.min()).toBe(-1);
	expect(tree.max()).toBe(20);
});

test('iteration', () => {
	let vals = [10, 10, 20, 5, -1];
	let tree = new RBTree(cmpInt);
	for (let v of vals){
		tree.insert(v);
	}
	let sorted = Array.from(new Set(vals)).sort(cmpInt);
	expect(getIteratorEls(tree.iterator())).toEqual(sorted);
	sorted.reverse()
	expect(getIteratorElsRev(tree.iterator())).toEqual(sorted);
});

test('find', () => {
	let tree = new RBTree(cmpInt);
	tree.insert(1);
	tree.insert(10);
	tree.insert(50);
	tree.insert(100);
	//
	expect(tree.find(40)).toBe(null);
	expect(tree.find(50)).toBe(50);
	expect(getIteratorEls(tree.lowerBound(10))).toEqual([10, 50, 100]);
	expect(getIteratorEls(tree.upperBound(10))).toEqual([50, 100]);
});
