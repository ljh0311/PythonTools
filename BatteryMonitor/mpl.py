import matplotlib.pyplot as plt

class graph_plot:
    def __init__(self, data):
        self.data = data

    def plot_graph(self, labels=None, title=None, legend=False):
        plt.plot(self.data, label="Data" if legend else None)
        if labels:
            plt.xlabel(labels[0])
            plt.ylabel(labels[1])
        if title:
            plt.title(title)
        if legend:
            plt.legend()
        plt.show()
        
    def plot_bar_graph(self, x=None, y=None, labels=None, title=None, legend=False, **kwargs):
        """
        Generic bar graph function.
        - x: Category labels or x-values (if None, use index).
        - y: Heights (if None, use self.data).
        - labels: tuple/list of (xlabel, ylabel) or None.
        - title: plot title or None.
        - legend: show legend if True.
        - **kwargs: passed to plt.bar.
        """
        if y is None:
            y = self.data
        if x is None:
            x = range(len(y))
        plt.bar(x, y, label="Data" if legend else None, **kwargs)

        # Labels
        if labels:
            if isinstance(labels, (list, tuple)) and len(labels) == 2:
                plt.xlabel(labels[0])
                plt.ylabel(labels[1])
            else:
                plt.xlabel('X')
                plt.ylabel('Y')
        else:
            plt.xlabel('X')
            plt.ylabel('Y')
        # Title
        if title:
            plt.title(title)
        if legend:
            plt.legend()
        plt.show()

    def plot_pie_chart(self, values=None, labels=None, title=None, legend=False, autopct='%1.1f%%', **kwargs):
        """
        Generic pie chart function.
        - values: iterable of values (if None, use self.data).
        - labels: labels for each slice.
        - title: title of the chart.
        - legend: show legend if True.
        - autopct: str or None for slice values.
        - **kwargs: passed to plt.pie.
        """
        if values is None:
            values = self.data
        patches, texts, autotexts = plt.pie(values, labels=labels, autopct=autopct if autopct else None, **kwargs)
        if title:
            plt.title(title)
        if legend:
            plt.legend()
        plt.show()
    
    def plot_scatter_plot(self, x=None, y=None, labels=None, title=None, legend=False, **kwargs):
        """
        Generic scatter plot function. 
        - x: data for x-axis (optional, if None assumes y is self.data)
        - y: data for y-axis (or None to use self.data as y)
        - labels: tuple/list of (xlabel, ylabel) or None
        - title: plot title or None
        - legend: whether to show legend
        - **kwargs: other matplotlib scatter kwargs
        """
        # Determine x and y data
        if x is not None and y is not None:
            plt.scatter(x, y, label="Data" if legend else None, **kwargs)
        elif x is not None:
            plt.scatter(range(len(x)), x, label="Data" if legend else None, **kwargs)
        elif y is not None:
            plt.scatter(range(len(y)), y, label="Data" if legend else None, **kwargs)
        else:
            plt.scatter(range(len(self.data)), self.data, label="Data" if legend else None, **kwargs)

        # Labels
        if labels:
            if isinstance(labels, (list, tuple)) and len(labels) == 2:
                plt.xlabel(labels[0])
                plt.ylabel(labels[1])
            else:
                plt.xlabel('X')
                plt.ylabel('Y')
        else:
            plt.xlabel('X')
            plt.ylabel('Y')
        # Title
        if title:
            plt.title(title)
        # Legend
        if legend:
            plt.legend()
        plt.show()