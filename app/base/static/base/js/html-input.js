class HTMLInput {
    selector;
    previousValue;

    constructor(selector, initValue = undefined) {
        this.selector = selector;
        this.previousValue = initValue;
    }

    getValue() {
        return $(this.selector)[0].value;
    }

    setValue(value) {
        $(this.selector)[0].value = value;
    }

    getParameterValue() {
        return this.getValue();
    }

    savePreviousValue() {
        this.previousValue = this.getValue();
    }

    setPreviousValue() {
        this.setValue(this.previousValue);
    }
}

class HTMLStaticField extends HTMLInput {
    value;

    constructor(value) {
        super();
        this.value = value;
    }

    getValue() {
        return this.value;
    }

    setValue(value) {
    }
}

class HTMLInputSelect extends HTMLInput {
}

class HTMLInputText extends HTMLInput {
    usePlaceholder;

    constructor(selector, initValue = undefined, usePlaceholder = false) {
        super(selector, initValue);
        this.usePlaceholder = usePlaceholder;
    }

    getValue() {
        let val = super.getValue(),
            placeholder = $(this.selector)[0].placeholder;
        if (this.usePlaceholder && val === "" && placeholder !== "") {
            return placeholder;
        }
        return val;
    }
}

class HTMLInputNumber extends HTMLInput {
}

class HTMLInputSwitch extends HTMLInput {
    getValue() {
        return $(this.selector)[0].checked;
    }

    setValue(value) {
        $(this.selector)[0].checked = value;
    }

    getParameterValue() {
        return this.getValue() ? 1 : 0;
    }
}

class HTMLInputRadio extends HTMLInput {
    // use a class for all radios as selector
    getValue() {
        return $(this.selector + ":checked")[0].value;
    }

    setValue(value) {
        $(this.selector).removeAttr('checked');
        $(this.selector + "[value=\"" + value + "\"]").attr('checked', true);
    }
}

class HTMLInputFile extends HTMLInput {
    getValue() {
        return $(this.selector).prop('files')[0];
    }

    setValue(value) {
        // Cannot set a value for input type file
    }

    clear() {
        $(this.selector).val('');
    }
}
