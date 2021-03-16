class HTMLInputGPUSelection extends HTMLInput {
    className;

    constructor(selector, className) {
        super(selector);
        this.className = className;
    }

    getValue() {
        let gpuList = [];
        $('#' + this.selector + 'Selection').find('.' + this.className + '-checkbox').each((_, element) => {
            if (!$(element).prop("disabled") && $(element).prop("checked")) {
                gpuList.push($(element).data("gpu-idx"));
            }
        });
        return gpuList.length === 0 ? null : gpuList;
    }

    setValue(value) {
        $('#' + this.selector + 'Selection').find('.' + this.className + '-checkbox').each((_, element) => {
            if (value.indexOf($(element).data("gpu-idx")) !== -1) {
                $(element).prop("checked", true);
            } else {
                $(element).prop("checked", false);
            }
        });
    }
}

/**
 * Class to provide client functionality for GPU selection HTML template
 */
class GPUSelection {
    id;
    className;
    lastGPUs = {"no":"sense"};

    /**
     * Constructor
     * @param {string} id the chosen id when including GPU selection HTML template
     * @param {string} className the chosen class when including GPU selection HTML template
     */
    constructor(id, className) {
        this.id = id;
        this.className = className;
    }

    /**
     * Setup/Create the HTML elements for the GPU selection based on received GPU information
     * @param {Object} gpuInfos the received information about GPUs
     */
    setupGPUSelection(gpuInfos) {
        let gpuSelector = $('#' + this.id + 'Selection');
        gpuSelector.empty();
        if (gpuInfos) {
            $('#' + this.id).removeClass('d-none');
            for (const [gpuName, gpuList] of Object.entries(gpuInfos)) {
                let gpuSelection = $('#' + this.id + 'Template').clone().removeClass("d-none");
                gpuSelection.attr("id", this.id + gpuName.replace(" ", ""));
                gpuSelection.find("." + this.className + "-name").text(gpuName);
                let gpuListHTML = gpuSelection.find("." + this.className + "-list");
                for (let i = 0; i < gpuList.length; i++) {
                    let gpuIdx = gpuList[i]["index"];
                    let gpuListItem = $('#' + this.id + 'TemplateListItem').clone().removeClass("d-none")
                    gpuListItem.attr("id", this.id + "Idx" + gpuIdx).addClass('d-inline-block');
                    gpuListItem.find("." + this.className + "-checkbox").attr("data-gpu-idx", gpuIdx);
                    gpuListItem.find("." + this.className + "-index").text(gpuIdx + 1);
                    if (!gpuList[i]["tf_comp"]) {
                        gpuListItem.find("." + this.className + "-checkbox").addClass("d-none")
                            .prop("disabled", true);
                        gpuListItem.find("." + this.className + "-warning").removeClass("d-none");
                        gpuListItem.removeClass("bg-transparent").addClass("bg-danger");
                        gpuListItem.attr("title", "This GPU is not compatible with TensorFlow");
                    }
                    gpuListHTML.append(gpuListItem);
                }
                gpuSelector.append(gpuSelection);
            }
        } else {
            $('#' + this.id).addClass('d-none');
        }
    }

    /**
     * Returns whether the "index"s of received GPU information are unique or not
     * @param {Object} gpuInfos the received information about GPUs
     * @returns {boolean} true if "index" are unique - false otherwise
     */
    isGPUIdxValid(gpuInfos) {
        if (gpuInfos) {
            let seenIdx = [];
            for (const [_, gpuList] of Object.entries(gpuInfos)) {
                for (let i = 0; i < gpuList.length; i++) {
                    if (seenIdx.indexOf(gpuList[i]['index']) !== -1) {
                        return false;
                    }
                    seenIdx.push(gpuList[i]['index']);
                }
            }
        }
        return true;
    }

    /**
     * Checks whether the GPU amount and names changes since the last call (this is required to determine whether to
     * rebuild the HTML DIV or not ["setupGPUSelection"])
     * @param {Object} gpuInfos the received information about GPUs
     * @returns {boolean} true if the GPU amount or names changes since the last call - false otherwise
     */
    isReceivedGPUElementsChanged(gpuInfos) {
        if (gpuInfos) {
            let compareGPUs = {};
            for (const [gpuName, gpuList] of Object.entries(gpuInfos)) {
                compareGPUs[gpuName] = gpuList.length;
            }
            if (JSON.stringify(compareGPUs) !== JSON.stringify(this.lastGPUs)) {
                this.lastGPUs = compareGPUs;
                return true;
            }
        } else {
            if (this.lastGPUs) {
                this.lastGPUs = null;
                return true;
            }
        }
        return false;
    }

    /**
     * Set the availability of GPUs based on received information (selection could be denied because free memory too
     * low). "setupGPUSelection" has to be called at least once before calling this method
     * @param {Object} gpuInfos the received information about GPUs
     */
    setGPUAvailability(gpuInfos) {
        if (gpuInfos) {
            for (const [_, gpuList] of Object.entries(gpuInfos)) {
                for (let i = 0; i < gpuList.length; i++) {
                    let gpuListItem = $('#' + this.id + 'Idx' + gpuList[i]['index']);
                    if (gpuList[i]['tf_comp']) {
                        if (gpuList[i]['ok']) {
                            gpuListItem.removeClass("bg-danger").addClass("bg-transparent");
                            gpuListItem.find("." + this.className + "-checkbox")
                                .prop("disabled", false);
                            gpuListItem.removeAttr("title");
                        } else {
                            gpuListItem.addClass("bg-danger").removeClass("bg-transparent");
                            gpuListItem.find("." + this.className + "-checkbox")
                                .prop("checked", false).prop("disabled", true);
                            gpuListItem.attr("title", "Not enough free memory available on this GPU");
                        }
                    }
                }
            }
        }
    }

    /**
     * Update the GPU selection frontend based on received information
     * @param {Object} gpuInfos the received information about GPUs
     * @param {boolean} locked true if the selection should be read only
     */
    updateGPUSelection(gpuInfos, locked = false) {
        if (this.isGPUIdxValid(gpuInfos)) {
            if (this.isReceivedGPUElementsChanged(gpuInfos)) {
                this.setupGPUSelection(gpuInfos);
            }
            this.setGPUSelectionLocked(gpuInfos, locked);
            if (!locked) {
                this.setGPUAvailability(gpuInfos);
            }
        } else {
            addMessage("Warning", "fa-exclamation-triangle text-warning",
                "Received invalid GPU information using asynchronous communication! " +
                "There has to be a bug if you were able to reproduce this warning!");
        }
    }

    /**
     * Set the selection read only
     * @param {Object} gpuInfos the received information about GPUs
     * @param {boolean} locked true if the selection should be read only
     */
    setGPUSelectionLocked(gpuInfos, locked) {
        if (gpuInfos) {
            for (const [_, gpuList] of Object.entries(gpuInfos)) {
                for (let i = 0; i < gpuList.length; i++) {
                    let gpuListItem = $('#' + this.id + 'Idx' + gpuList[i]['index']);
                    if (locked) {
                        gpuListItem.removeClass("bg-transparent bg-danger");
                        gpuListItem.find("." + this.className + "-checkbox").prop("disabled", true);
                        if (gpuList[i]["tf_comp"]) {
                            gpuListItem.removeAttr("title");
                        }
                    } else {
                        if (gpuList[i]["tf_comp"]) {
                            gpuListItem.addClass("bg-transparent");
                        } else {
                            gpuListItem.addClass("bg-danger");
                        }
                        gpuListItem.find("." + this.className + "-checkbox").prop("disabled", true);
                    }
                }
            }
        }
    }
}