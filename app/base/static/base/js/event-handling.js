class EventHandling {
    triggers = {};

    on(event, callback) {
        if (!this.triggers[event])
            this.triggers[event] = [];
        this.triggers[event].push(callback);
    }

    off(event, callback) {
        if (this.triggers[event]) {
            let idx = this.triggers[event].indexOf(callback);
            if (idx > -1) {
                this.triggers[event].splice(idx, 1);
            }
        }
    }

    triggerHandler(event, ...params) {
        let allOk = true;
        if (this.triggers[event]) {
            this.triggers[event].forEach((item, index) => {
                if (!item(...params)) {
                    allOk = false;
                    return false;
                }
            });
        }
        return allOk;
    }
}