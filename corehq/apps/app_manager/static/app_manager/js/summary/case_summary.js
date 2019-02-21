hqDefine('app_manager/js/summary/case_summary',[
    'jquery',
    'underscore',
    'knockout',
    'hqwebapp/js/initial_page_data',
    'hqwebapp/js/assert_properties',
    'app_manager/js/summary/models',
    'app_manager/js/menu',  // enable lang switcher and "Updates to publish" banner
    'hqwebapp/js/knockout_bindings.ko', // popover
], function ($, _, ko, initialPageData, assertProperties, models) {

    var caseTypeModel = function (caseType, showCalculations) {
        var self = models.contentItemModel(caseType);

        self.properties = _.map(caseType.properties, function (property) {
            return models.contentItemModel(property);
        });

        self.visibleProperties = ko.computed(function () {
            return _.filter(self.properties, function (property) {
                // only show case list / detail calculated properties if calculations are turned on
                return showCalculations() || !property.is_detail_calculation;
            });
        });

        // Convert these from objects to lists so knockout can process more easily
        self.relationshipList = _.map(_.keys(self.relationships), function (relationship) {
            return {
                relationship: relationship,
                caseType: self.relationships[relationship],
            };
        });
        self.openedByList = _.map(_.keys(self.opened_by), function (formId) {
            return {
                formId: formId,
                conditions: self.opened_by[formId].conditions,
            };
        });
        self.closedByList = _.map(_.keys(self.closed_by), function (formId) {
            return {
                formId: formId,
                conditions: self.closed_by[formId].conditions,
            };
        });

        return self;
    };

    var caseSummaryModel = function (options) {
        var self = models.contentModel(_.extend(options, {
            query_label: gettext("Filter properties"),
            onQuery: function (query) {
                query = query.trim().toLowerCase();
                _.each(self.caseTypes, function (caseType) {
                    var hasVisible = false;
                    _.each(caseType.properties, function (property) {
                        var isVisible = !query || property.name.indexOf(query) !== -1;
                        property.matchesQuery(isVisible);
                        self.showCalculations(self.showCalculations() || (query && isVisible && property.is_detail_calculation));
                        hasVisible = hasVisible || isVisible;
                    });
                    caseType.matchesQuery(hasVisible || !query && !caseType.properties.length);
                });
            },
            onSelectMenuItem: function (selectedId) {
                _.each(self.caseTypes, function (caseType) {
                    caseType.isSelected(!selectedId || selectedId === caseType.name);
                });
            },
        }));

        self.showConditions = ko.observable(false);
        self.toggleConditions = function () {
            self.showConditions(!self.showConditions());
        };

        self.showCalculations = ko.observable(false);
        self.toggleCalculations = function () {
            self.showCalculations(!self.showCalculations());
        };

        assertProperties.assertRequired(options, ['case_types']);
        self.caseTypes = _.map(options.case_types, function (caseType) {
            return caseTypeModel(caseType, self.showCalculations);
        });

        return self;
    };

    $(function () {
        var caseTypes = initialPageData.get("case_metadata").case_types;

        var caseSummaryMenu = models.menuModel({
            items: _.map(caseTypes, function (caseType) {
                return models.menuItemModel({
                    id: caseType.name,
                    name: caseType.name,
                    icon: "fcc fcc-fd-external-case appnav-primary-icon",
                    has_errors: caseType.has_errors,
                    subitems: [],
                });
            }),
            viewAllItems: gettext("View All Cases"),
        });

        var caseSummaryContent = caseSummaryModel({
            case_types: caseTypes,
            form_name_map: initialPageData.get("form_name_map"),
            lang: initialPageData.get("lang"),
            langs: initialPageData.get("langs"),
            read_only: initialPageData.get("read_only"),
        });

        models.initSummary(caseSummaryMenu, caseSummaryContent);
    });
});
