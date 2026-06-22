export namespace main {
	
	export class Overview {
	    dbPath: string;
	    total: number;
	    categories: string[];
	    accent: string;
	    runtimeNote: string;
	
	    static createFrom(source: any = {}) {
	        return new Overview(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.dbPath = source["dbPath"];
	        this.total = source["total"];
	        this.categories = source["categories"];
	        this.accent = source["accent"];
	        this.runtimeNote = source["runtimeNote"];
	    }
	}
	export class ScanOptions {
	    customPath: string;
	    includeStartMenu: boolean;
	    limit: number;
	
	    static createFrom(source: any = {}) {
	        return new ScanOptions(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.customPath = source["customPath"];
	        this.includeStartMenu = source["includeStartMenu"];
	        this.limit = source["limit"];
	    }
	}
	export class ScanResult {
	    name: string;
	    exePath: string;
	    lnkPath: string;
	    sourceType: string;
	    rootPath: string;
	    category: string;
	    status: string;
	    selected: boolean;
	
	    static createFrom(source: any = {}) {
	        return new ScanResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.exePath = source["exePath"];
	        this.lnkPath = source["lnkPath"];
	        this.sourceType = source["sourceType"];
	        this.rootPath = source["rootPath"];
	        this.category = source["category"];
	        this.status = source["status"];
	        this.selected = source["selected"];
	    }
	}
	export class Shortcut {
	    id: number;
	    name: string;
	    exePath: string;
	    lnkPath: string;
	    args: string;
	    sourceType: string;
	    category: string;
	    runCount: number;
	    addedAt: string;
	
	    static createFrom(source: any = {}) {
	        return new Shortcut(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.exePath = source["exePath"];
	        this.lnkPath = source["lnkPath"];
	        this.args = source["args"];
	        this.sourceType = source["sourceType"];
	        this.category = source["category"];
	        this.runCount = source["runCount"];
	        this.addedAt = source["addedAt"];
	    }
	}
	export class ShortcutFilter {
	    category: string;
	    query: string;
	    sortBy: string;
	
	    static createFrom(source: any = {}) {
	        return new ShortcutFilter(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.category = source["category"];
	        this.query = source["query"];
	        this.sortBy = source["sortBy"];
	    }
	}

}

