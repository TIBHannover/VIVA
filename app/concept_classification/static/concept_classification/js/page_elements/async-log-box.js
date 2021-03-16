/**
 * Class to provide client functionality for front end logging which is embedded in an collapsable accordion
 */
class AsyncLogBox extends AsyncLog {
    /**
     * Constructor parameters identical to parent class - see parent class documentation for more information
     */
    constructor(id, urlSse, urlLog, sseType) {
        super(id, urlSse, urlLog, sseType);
        $('#' + this.id + 'BoxButton').on('click',
                _ => setTimeout(() => this.scrollLogToBottom(), 500));
    }
}