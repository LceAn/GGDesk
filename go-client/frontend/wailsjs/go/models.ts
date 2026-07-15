export namespace main {
	
	export class BackupReport {
	    path: string;
	    size: number;
	
	    static createFrom(source: any = {}) {
	        return new BackupReport(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.path = source["path"];
	        this.size = source["size"];
	    }
	}
	export class DuplicateItem {
	    id: number;
	    name: string;
	    exePath: string;
	    lnkPath: string;
	    sourceType: string;
	    category: string;
	    runCount: number;
	    score: number;
	    keep: boolean;
	
	    static createFrom(source: any = {}) {
	        return new DuplicateItem(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.exePath = source["exePath"];
	        this.lnkPath = source["lnkPath"];
	        this.sourceType = source["sourceType"];
	        this.category = source["category"];
	        this.runCount = source["runCount"];
	        this.score = source["score"];
	        this.keep = source["keep"];
	    }
	}
	export class DuplicateGroup {
	    key: string;
	    items: DuplicateItem[];
	    reason: string;
	
	    static createFrom(source: any = {}) {
	        return new DuplicateGroup(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.key = source["key"];
	        this.items = this.convertValues(source["items"], DuplicateItem);
	        this.reason = source["reason"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class DedupResult {
	    groups: DuplicateGroup[];
	    total: number;
	
	    static createFrom(source: any = {}) {
	        return new DedupResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.groups = this.convertValues(source["groups"], DuplicateGroup);
	        this.total = source["total"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	
	
	export class GenerateReport {
	    outputPath: string;
	    created: number;
	    added: number;
	    failures: string[];
	
	    static createFrom(source: any = {}) {
	        return new GenerateReport(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.outputPath = source["outputPath"];
	        this.created = source["created"];
	        this.added = source["added"];
	        this.failures = source["failures"];
	    }
	}
	export class OutputShortcut {
	    name: string;
	    target: string;
	    path: string;
	
	    static createFrom(source: any = {}) {
	        return new OutputShortcut(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.target = source["target"];
	        this.path = source["path"];
	    }
	}
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
	export class ScanExeInfo {
	    path: string;
	    name: string;
	    size: number;
	    relPath: string;
	
	    static createFrom(source: any = {}) {
	        return new ScanExeInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.path = source["path"];
	        this.name = source["name"];
	        this.size = source["size"];
	        this.relPath = source["relPath"];
	    }
	}
	export class ScanOptions {
	    customPath: string;
	    includeStartMenu: boolean;
	    includeUWP: boolean;
	    limit: number;
	
	    static createFrom(source: any = {}) {
	        return new ScanOptions(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.customPath = source["customPath"];
	        this.includeStartMenu = source["includeStartMenu"];
	        this.includeUWP = source["includeUWP"];
	        this.limit = source["limit"];
	    }
	}
	export class ScanResult {
	    name: string;
	    exePath: string;
	    lnkPath: string;
	    args: string;
	    selectedExes: string[];
	    allExes: ScanExeInfo[];
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
	        this.args = source["args"];
	        this.selectedExes = source["selectedExes"];
	        this.allExes = this.convertValues(source["allExes"], ScanExeInfo);
	        this.sourceType = source["sourceType"];
	        this.rootPath = source["rootPath"];
	        this.category = source["category"];
	        this.status = source["status"];
	        this.selected = source["selected"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class SettingsBundle {
	    settings: Record<string, string>;
	    rules: Record<string, string>;
	    lists: Record<string, Array<string>>;
	    paths: Record<string, string>;
	
	    static createFrom(source: any = {}) {
	        return new SettingsBundle(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.settings = source["settings"];
	        this.rules = source["rules"];
	        this.lists = source["lists"];
	        this.paths = source["paths"];
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

