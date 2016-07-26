/* globals analytics */

hqDefine('export/js/models.js', function () {
    var constants = hqImport('export/js/const.js');
    var utils = hqImport('export/js/utils.js');

    var ExportInstance = function(instanceJSON, options) {
        options = options || {};
        var self = this;
        ko.mapping.fromJS(instanceJSON, ExportInstance.mapping, self);
        self.saveState = ko.observable(constants.SAVE_STATES.READY);
        self.saveUrl = options.saveUrl;
        // If any column has a deid transform, show deid column
        self.isDeidColumnVisible = ko.observable(self.is_deidentified() || _.any(self.tables(), function(table) {
            return table.selected() && _.any(table.columns(), function(column) {
                return column.selected() && column.deid_transform();
            });
        }));
    };

    ExportInstance.prototype.getFormatOptionValues = function() {
        return _.map(constants.EXPORT_FORMATS, function(value) { return value; });
    };

    ExportInstance.prototype.getFormatOptionText = function(format) {
        if (format === constants.EXPORT_FORMATS.HTML) {
            return gettext('Web Page (Excel Dashboards)');
        } else if (format === constants.EXPORT_FORMATS.CSV) {
            return gettext('CSV (Zip file)');
        } else if (format === constants.EXPORT_FORMATS.XLS) {
            return gettext('Excel (older versions)');
        } else if (format === constants.EXPORT_FORMATS.XLSX) {
            return gettext('Excel 2007');
        }
    };

    ExportInstance.prototype.isNew = function() {
        return !ko.utils.unwrapObservable(this._id);
    };

    ExportInstance.prototype.getSaveText = function() {
        return this.isNew() ? gettext('Create') : gettext('Save');
    };

    ExportInstance.prototype.save = function() {
        var self = this,
            serialized;

        self.saveState(constants.SAVE_STATES.SAVING);
        serialized = self.toJS();
        $.post(self.saveUrl, JSON.stringify(serialized))
            .success(function(data) {
                self.recordSaveAnalytics(function() {
                    self.saveState(constants.SAVE_STATES.SUCCESS);
                    utils.redirect(data.redirect);
                });
            })
            .fail(function() {
                self.saveState(constants.SAVE_STATES.ERROR);
            });
    };

    ExportInstance.prototype.recordSaveAnalytics = function(callback) {
        var analyticsAction = this.is_daily_saved_export() ? 'Saved' : 'Regular',
            analyticsExportType = _.capitalize(this.type()),
            args,
            eventCategory;

        analytics.usage("Create Export", analyticsExportType, analyticsAction);
        if (this.export_format === constants.EXPORT_FORMATS.HTML) {
            args = ["Create Export", analyticsExportType, 'Excel Dashboard'];
            // If it's not new then we have to add the callback in to redirect
            if (!this.isNew()) {
                args.push(callback);
            }
            analytics.usage.apply(null, args);
        }
        if (this.isNew()) {
            eventCategory = constants.ANALYTICS_EVENT_CATEGORIES[this.type()];
            analytics.usage(eventCategory, 'Custom export creation', '');
            analytics.workflow("Clicked 'Create' in export edit page", callback);
        } else if (this.export_format !== constants.EXPORT_FORMATS.HTML) {
            callback();
        }
    };

    ExportInstance.prototype.showDeidColumn = function() {
        utils.animateToEl('#field-select', function() {
            this.isDeidColumnVisible(true);
        }.bind(this));
    };

    ExportInstance.prototype.toJS = function() {
        return ko.mapping.toJS(this, ExportInstance.mapping);
    };

    /**
     * addUserDefinedTableConfiguration
     *
     * This will add a new table to the export configuration and seed it with
     * one column, row number.
     *
     * @param {ExportInstance} instance
     * @param {Object} e - The window's click event
     */
    ExportInstance.prototype.addUserDefinedTableConfiguration = function(instance, e) {
        e.preventDefault();
        instance.tables.push(new UserDefinedTableConfiguration({
            selected: true,
            doc_type: 'TableConfiguration',
            label: 'Sheet',
            is_user_defined: true,
            path: [],
            columns: [
                {
                    doc_type: 'RowNumberColumn',
                    tags: ['row'],
                    item: {
                        doc_type: 'ExportItem',
                        path: [{
                            doc_type: 'PathNode',
                            name: 'number',
                        }]
                    },
                    selected: true,
                    is_advanced: false,
                    label: 'number',
                    deid_transform: null,
                    repeat: null,
                },
            ],
        }));
    };

    ExportInstance.mapping = {
        include: [
            '_id',
            'name',
            'tables',
            'type',
            'export_format',
            'split_multiselects',
            'transform_dates',
            'include_errors',
            'is_deidentified',
            'is_daily_saved_export',
        ],
        tables: {
            create: function(options) {
                if (options.data.is_user_defined) {
                    return new UserDefinedTableConfiguration(options.data);
                } else {
                    return new TableConfiguration(options.data);
                }
            },
        },
    };

    var TableConfiguration = function(tableJSON) {
        var self = this;
        self.showAdvanced = ko.observable(false);
        ko.mapping.fromJS(tableJSON, TableConfiguration.mapping, self);
    };

    TableConfiguration.prototype.isVisible = function() {
        // Not implemented
        return true;
    };

    TableConfiguration.prototype.toggleShowAdvanced = function(table) {
        table.showAdvanced(!table.showAdvanced());
    };

    TableConfiguration.prototype._select = function(select) {
        _.each(this.columns(), function(column) {
            column.selected(select && column.isVisible(this));
        }.bind(this));
    };

    TableConfiguration.prototype.selectAll = function(table) {
        table._select(true);
    };

    TableConfiguration.prototype.selectNone = function(table) {
        table._select(false);
    };

    TableConfiguration.prototype.useLabels = function(table) {
        _.each(table.columns(), function(column) {
            if (column.isQuestion() && !column.isUserDefined) {
                column.label(column.item.label() || column.label());
            }
        });
    };

    TableConfiguration.prototype.useIds = function(table) {
        _.each(table.columns(), function(column) {
            if (column.isQuestion() && !column.isUserDefined) {
                column.label(column.item.readablePath() || column.label());
            }
        });
    };

    TableConfiguration.prototype.getColumn = function(path) {
        return _.find(this.columns(), function(column) {
            return utils.readablePath(column.item.path()) === path;
        });
    };

    TableConfiguration.prototype.addUserDefinedExportColumn = function(table, e) {
        e.preventDefault();
        table.columns.push(new UserDefinedExportColumn({
            selected: true,
            deid_transform: null,
            doc_type: 'UserDefinedExportColumn',
            label: '',
            custom_path: [],
        }));
    };

    TableConfiguration.mapping = {
        include: ['name', 'path', 'columns', 'selected', 'label', 'is_deleted', 'doc_type', 'is_user_defined'],
        columns: {
            create: function(options) {
                if (options.data.doc_type === 'UserDefinedExportColumn') {
                    return new UserDefinedExportColumn(options.data);
                } else {
                    return new ExportColumn(options.data);
                }
            },
        },
        path: {
            create: function(options) {
                return new PathNode(options.data);
            },
        },
    };

    /**
     * UserDefinedTableConfiguration
     * @class
     *
     * This represents a table configuration that has been defined by the user. It
     * is very similar to a TableConfiguration except that the user defines the
     * path to where the new sheet should be.
     *
     * The customPathString for a table should always end in [] since a new export
     * table should be an array.
     *
     * When specifying questions/properties in a user defined table, you'll need
     * to include the base table path in the property. For example:
     *
     * table path: form.repeat[]
     * question path: form.repeat[].question1
     */
    var UserDefinedTableConfiguration = function(tableJSON) {
        var self = this;
        ko.mapping.fromJS(tableJSON, TableConfiguration.mapping, self);
        self.customPathString = ko.observable(utils.readablePath(self.path()));
        self.customPathString.extend({
            required: true,
            pattern: {
                message: gettext('The table path should end with []'),
                params: /^.*\[\]$/,
            },
        });

        self.showAdvanced = ko.observable(false);
        self.customPathString.subscribe(self.onCustomPathChange.bind(self));
    };
    UserDefinedTableConfiguration.prototype = Object.create(TableConfiguration.prototype);

    UserDefinedTableConfiguration.prototype.onCustomPathChange = function() {
        var rowColumn,
            nestedRepeatCount;
        this.path(utils.customPathToNodes(this.customPathString()));

        // Update the rowColumn's repeat count by counting the number of
        // repeats in the table path
        nestedRepeatCount = _.filter(this.path(), function(node) { return node.is_repeat(); }).length;
        rowColumn = this.getColumn('number');
        if (rowColumn) {
            rowColumn.repeat(nestedRepeatCount);
        }
    };

    var ExportColumn = function(columnJSON) {
        var self = this;
        ko.mapping.fromJS(columnJSON, ExportColumn.mapping, self);
        self.showOptions = ko.observable(false);
        self.userDefinedOptionToAdd = ko.observable('');
        self.isUserDefined = false;
    };

    ExportColumn.prototype.isQuestion = function() {
        var disallowedTags = ['info', 'case', 'server', 'row', 'app', 'stock'],
            self = this;
        return !_.any(disallowedTags, function(tag) { return _.include(self.tags(), tag); });
    };

    ExportColumn.prototype.addUserDefinedOption = function() {
        var option = this.userDefinedOptionToAdd();
        if (option) {
            this.user_defined_options.push(option);
        }
        this.userDefinedOptionToAdd('');
    };

    ExportColumn.prototype.removeUserDefinedOption = function(option) {
        this.user_defined_options.remove(option);
    };

    ExportColumn.prototype.formatProperty = function() {
        if (this.tags().length !== 0){
            return this.label();
        } else {
            return _.map(this.item.path(), function(node) { return node.name(); }).join('.');
        }
    };

    ExportColumn.prototype.getDeidOptions = function() {
        return _.map(constants.DEID_OPTIONS, function(value) { return value; });
    };

    ExportColumn.prototype.getDeidOptionText = function(deidOption) {
        if (deidOption === constants.DEID_OPTIONS.ID) {
            return gettext('Sensitive ID');
        } else if (deidOption === constants.DEID_OPTIONS.DATE) {
            return gettext('Sensitive Date');
        } else if (deidOption === constants.DEID_OPTIONS.NONE) {
            return gettext('None');
        }
    };

    ExportColumn.prototype.isVisible = function(table) {
        return table.showAdvanced() || (!this.is_advanced() || this.selected());
    };

    ExportColumn.prototype.isCaseName = function() {
        return this.item.isCaseName();
    };

    ExportColumn.prototype.translatedHelp = function() {
        return gettext(this.help_text);
    };

    ExportColumn.mapping = {
        include: [
            'item',
            'label',
            'is_advanced',
            'selected',
            'tags',
            'deid_transform',
            'help_text',
            'split_type',
            'user_defined_options',
        ],
        item: {
            create: function(options) {
                return new ExportItem(options.data);
            },
        },
    };

    /*
     * UserDefinedExportColumn
     *
     * This model represents a column that a user has defined the path to the
     * data within the form. It should only be needed for RemoteApps
     */
    var UserDefinedExportColumn = function(columnJSON) {
        var self = this;
        ko.mapping.fromJS(columnJSON, UserDefinedExportColumn.mapping, self);
        self.showOptions = ko.observable(false);
        self.isUserDefined = true;
        self.customPathString = ko.observable(utils.readablePath(self.custom_path())).extend({
            required: true,
        });
        self.customPathString.subscribe(self.customPathToNodes.bind(self));
    };
    UserDefinedExportColumn.prototype = Object.create(ExportColumn.prototype);

    UserDefinedExportColumn.prototype.isVisible = function() {
        return true;
    };

    UserDefinedExportColumn.prototype.customPathToNodes = function() {
        this.custom_path(utils.customPathToNodes(this.customPathString()));
    };

    UserDefinedExportColumn.mapping = {
        include: [
            'selected',
            'deid_transform',
            'doc_type',
            'custom_path',
            'label',
        ],
        custom_path: {
            create: function(options) {
                return new PathNode(options.data);
            },
        },
    };

    var ExportItem = function(itemJSON) {
        var self = this;
        ko.mapping.fromJS(itemJSON, ExportItem.mapping, self);
    };

    ExportItem.prototype.isCaseName = function() {
        return this.path()[this.path().length - 1].name === 'name';
    };

    ExportItem.prototype.readablePath = function() {
        return utils.readablePath(this.path());
    };

    ExportItem.mapping = {
        include: ['path', 'label', 'tag'],
        path: {
            create: function(options) {
                return new PathNode(options.data);
            },
        },
    };

    var PathNode = function(pathNodeJSON) {
        ko.mapping.fromJS(pathNodeJSON, PathNode.mapping, this);
    };

    PathNode.mapping = {
        include: ['name', 'is_repeat'],
    };

    return {
        ExportInstance: ExportInstance,
        ExportColumn: ExportColumn,
        ExportItem: ExportItem,
        PathNode: PathNode,
    };

});
