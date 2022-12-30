export {}

// Temporary solution for typescript not including Array.findLast()
declare global {
	interface Array<T> {
		findLast(
			predicate: (value: T, index: number, obj: T[]) => unknown,
			thisArg?: any
		): T | undefined
	}
}
